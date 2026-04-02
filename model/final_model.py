import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import joblib

from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import StratifiedKFold, train_test_split
from xgboost import XGBClassifier

# =========================================================
# 0. 경로 및 환경 설정
# =========================================================
BASE_PATH = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'raw')

# =========================================================
# 1. 데이터 로드 (상대 경로 적용)
# =========================================================
def load_data():
    print(f"📦 데이터 로드 중 (상대 경로): {BASE_PATH}")
    train_members = pd.read_csv(os.path.join(BASE_PATH, 'train_members_v2.csv'))
    transactions = pd.read_csv(os.path.join(BASE_PATH, 'transactions_v2.csv'))
    user_logs = pd.read_csv(os.path.join(BASE_PATH, 'user_logs_aug_v2.csv'))
    return train_members, transactions, user_logs


# =========================================================
# 2. 기본 전처리
# =========================================================
def basic_preprocess(train_members, transactions, user_logs):
    train_members = train_members.drop_duplicates(subset=['msno'], keep='first').copy()
    transactions = transactions.drop_duplicates().copy()
    user_logs = user_logs.drop_duplicates().copy()

    train_members['gender'] = train_members['gender'].map({'female': 0, 'male': 1})

    for col in ['city', 'registered_via']:
        train_members[col] = train_members[col].astype('category')

    train_members['registration_init_time'] = pd.to_datetime(train_members['registration_init_time'])
    transactions['transaction_date'] = pd.to_datetime(transactions['transaction_date'], format='%Y-%m-%d')
    transactions['membership_expire_date'] = pd.to_datetime(transactions['membership_expire_date'], format='%Y-%m-%d')
    user_logs['date'] = pd.to_datetime(user_logs['date'], format='%Y-%m-%d')

    median_age = train_members[(train_members['bd'] > 0) & (train_members['bd'] < 100)]['bd'].median()
    train_members.loc[(train_members['bd'] <= 0) | (train_members['bd'] >= 100), 'bd'] = median_age

    return train_members, transactions, user_logs


# =========================================================
# 3. transactions 변수 생성
# =========================================================
def make_transaction_features(transactions, cutoff_date=pd.Timestamp('2017-02-28')):
    transactions = transactions.sort_values(['msno', 'transaction_date']).copy()

    transactions['discount_amount'] = transactions['plan_list_price'] - transactions['actual_amount_paid']
    transactions['discount_rate'] = np.where(
        transactions['plan_list_price'] > 0,
        transactions['discount_amount'] / transactions['plan_list_price'],
        0
    )
    transactions['has_discount'] = (transactions['discount_amount'] > 0).astype(int)

    transactions_features = transactions.groupby('msno').agg(
        payment_method_id_last=('payment_method_id', 'last'),
        payment_method_id_nunique=('payment_method_id', 'nunique'),
        payment_plan_days_last=('payment_plan_days', 'last'),
        payment_plan_days_mean=('payment_plan_days', 'mean'),
        payment_plan_days_std=('payment_plan_days', 'std'),
        actual_amount_paid_last=('actual_amount_paid', 'last'),
        actual_amount_paid_mean=('actual_amount_paid', 'mean'),
        actual_amount_paid_std=('actual_amount_paid', 'std'),
        plan_list_price_last=('plan_list_price', 'last'),
        is_auto_renew_last=('is_auto_renew', 'last'),
        is_auto_renew_rate=('is_auto_renew', 'mean'),
        is_cancel_last=('is_cancel', 'last'),
        is_cancel_rate=('is_cancel', 'mean'),
        trans_count=('transaction_date', 'count'),
        last_transaction_date=('transaction_date', 'max'),
        first_transaction_date=('transaction_date', 'min'),
        last_membership_expire_date=('membership_expire_date', 'last'),
        discount_rate_mean=('discount_rate', 'mean'),
        discount_rate_last=('discount_rate', 'last'),
        has_discount_rate=('has_discount', 'mean')
    ).reset_index()

    transactions_features['days_since_last_txn'] = (cutoff_date - transactions_features['last_transaction_date']).dt.days
    transactions_features['days_until_expire'] = (transactions_features['last_membership_expire_date'] - cutoff_date).dt.days
    transactions_features['last_payment_gap'] = (transactions_features['last_membership_expire_date'] - transactions_features['last_transaction_date']).dt.days
    transactions_features['txn_span_days'] = (transactions_features['last_transaction_date'] - transactions_features['first_transaction_date']).dt.days
    transactions_features['expiry_before_cutoff_flag'] = (transactions_features['last_membership_expire_date'] < cutoff_date).astype(int)

    transactions_features = transactions_features.drop(columns=['last_transaction_date', 'first_transaction_date', 'last_membership_expire_date'])

    last2 = transactions.groupby('msno').tail(2).copy()
    last2['txn_rank'] = last2.groupby('msno').cumcount()
    last2_num = last2.pivot(index='msno', columns='txn_rank', values=['actual_amount_paid', 'payment_plan_days'])
    last2_num.columns = [f'{col}_{rank}' for col, rank in last2_num.columns]
    last2_num = last2_num.reset_index()
    last2_date = last2.pivot(index='msno', columns='txn_rank', values=['transaction_date', 'membership_expire_date'])
    last2_date.columns = [f'{col}_{rank}' for col, rank in last2_date.columns]
    last2_date = last2_date.reset_index()
    last2_pivot = last2_num.merge(last2_date, on='msno', how='left')

    for col in ['actual_amount_paid_0', 'actual_amount_paid_1', 'payment_plan_days_0', 'payment_plan_days_1']:
        if col in last2_pivot.columns:
            last2_pivot[col] = pd.to_numeric(last2_pivot[col], errors='coerce')

    last2_pivot['actual_paid_change_last2'] = (last2_pivot['actual_amount_paid_1'] - last2_pivot['actual_amount_paid_0'])
    last2_pivot['plan_days_change_last2'] = (last2_pivot['payment_plan_days_1'] - last2_pivot['payment_plan_days_0'])
    last2_pivot['txn_gap_last2'] = (pd.to_datetime(last2_pivot['transaction_date_1']) - pd.to_datetime(last2_pivot['transaction_date_0'])).dt.days
    last2_pivot['expire_gap_change_last2'] = (pd.to_datetime(last2_pivot['membership_expire_date_1']) - pd.to_datetime(last2_pivot['membership_expire_date_0'])).dt.days

    transactions_features = transactions_features.merge(last2_pivot[['msno', 'actual_paid_change_last2', 'plan_days_change_last2', 'txn_gap_last2', 'expire_gap_change_last2']], on='msno', how='left')

    return transactions_features


# =========================================================
# 4. 결제 후 첫 청취 변수 생성
# =========================================================
def make_listen_after_txn_features(transactions, user_logs):
    txn_tmp = transactions[['msno', 'transaction_date']].sort_values(['transaction_date', 'msno']).copy()
    log_tmp = user_logs[['msno', 'date']].sort_values(['date', 'msno']).copy()

    txn_after_listen = pd.merge_asof(txn_tmp, log_tmp, by='msno', left_on='transaction_date', right_on='date', direction='forward', allow_exact_matches=False)
    txn_after_listen.rename(columns={'date': 'first_listen_after_txn'}, inplace=True)
    txn_after_listen['days_to_first_listen_after_txn'] = (txn_after_listen['first_listen_after_txn'] - txn_after_listen['transaction_date']).dt.days
    txn_after_listen['listen_within_7d_after_txn'] = (txn_after_listen['days_to_first_listen_after_txn'] <= 7).astype(float)
    txn_after_listen['listen_within_30d_after_txn'] = (txn_after_listen['days_to_first_listen_after_txn'] <= 30).astype(float)
    txn_after_listen.loc[txn_after_listen['days_to_first_listen_after_txn'].isna(), ['listen_within_7d_after_txn', 'listen_within_30d_after_txn']] = 0

    listen_after_txn_features = txn_after_listen.groupby('msno').agg(
        mean_days_to_first_listen_after_txn=('days_to_first_listen_after_txn', 'mean'),
        last_days_to_first_listen_after_txn=('days_to_first_listen_after_txn', 'last'),
        listen_within_7d_after_txn_rate=('listen_within_7d_after_txn', 'mean'),
        listen_within_30d_after_txn_rate=('listen_within_30d_after_txn', 'mean')
    ).reset_index()

    return listen_after_txn_features


# =========================================================
# 5. user_logs 변수 생성
# =========================================================
def make_log_window_features(df, cutoff_date, days):
    sub = df[df['date'] >= cutoff_date - pd.Timedelta(days=days - 1)].copy()
    feat = sub.groupby('msno').agg(
        **{
            f'active_days_{days}': ('date', 'nunique'),
            f'total_secs_{days}': ('total_secs', 'sum'),
            f'total_secs_mean_{days}': ('total_secs', 'mean'),
            f'play_total_{days}': ('play_total', 'sum'),
            f'num_unq_{days}': ('num_unq', 'sum'),
            f'num_100_{days}': ('num_100', 'sum')
        }
    ).reset_index()
    feat[f'completion_ratio_{days}'] = (feat[f'num_100_{days}'] / feat[f'play_total_{days}'].replace(0, np.nan))
    feat[f'unique_ratio_{days}'] = (feat[f'num_unq_{days}'] / feat[f'play_total_{days}'].replace(0, np.nan))
    return feat.drop(columns=[f'num_100_{days}'])


def make_log_features(user_logs, cutoff_date=pd.Timestamp('2017-02-28')):
    user_logs = user_logs.copy()
    user_logs['play_total'] = user_logs[['num_25', 'num_50', 'num_75', 'num_985', 'num_100']].sum(axis=1)
    log_all = user_logs.groupby('msno').agg(
        active_days_all=('date', 'nunique'),
        num_25_all=('num_25', 'sum'),
        num_50_all=('num_50', 'sum'),
        num_75_all=('num_75', 'sum'),
        num_985_all=('num_985', 'sum'),
        num_100_all=('num_100', 'sum'),
        num_unq_all=('num_unq', 'sum'),
        total_secs_all=('total_secs', 'sum'),
        total_secs_mean_all=('total_secs', 'mean'),
        play_total_all=('play_total', 'sum')
    ).reset_index()
    log_all['completion_ratio_all'] = (log_all['num_100_all'] / log_all['play_total_all'].replace(0, np.nan))
    log_all['unique_ratio_all'] = (log_all['num_unq_all'] / log_all['play_total_all'].replace(0, np.nan))
    log_7 = make_log_window_features(user_logs, cutoff_date, 7)
    log_30 = make_log_window_features(user_logs, cutoff_date, 30)
    log_features = log_all.merge(log_7, on='msno', how='left')
    log_features = log_features.merge(log_30, on='msno', how='left')
    return log_features


# =========================================================
# 6. 병합 + 최종 모델링용 데이터셋 생성
# =========================================================
def build_modeling_dataframe():
    cutoff_date = pd.Timestamp('2017-02-28')
    train_members, transactions, user_logs = load_data()
    train_members, transactions, user_logs = basic_preprocess(train_members, transactions, user_logs)
    transactions_features = make_transaction_features(transactions, cutoff_date=cutoff_date)
    listen_after_txn_features = make_listen_after_txn_features(transactions, user_logs)
    log_features = make_log_features(user_logs, cutoff_date=cutoff_date)
    merge_df = train_members.merge(transactions_features, on='msno', how='left')
    merge_df = merge_df.merge(log_features, on='msno', how='left')
    merge_df = merge_df.merge(listen_after_txn_features, on='msno', how='left')
    merge_df_raw = merge_df.copy()
    ref_date = merge_df['registration_init_time'].max()
    merge_df['tenure'] = (ref_date - merge_df['registration_init_time']).dt.days
    merge_df = merge_df.drop(columns=['registration_init_time'])
    return merge_df, merge_df_raw


# =========================================================
# 7. 모델 공통용 숫자형 정리
# =========================================================
def finalize_numeric_features(df):
    df = df.copy()
    df = df.replace([np.inf, -np.inf], np.nan)

    # category -> 숫자형 유지가 어려운 경우를 위해 dummies 처리
    df = pd.get_dummies(
        df,
        columns=['city', 'registered_via', 'payment_method_id_last', 'gender'],
        drop_first=True
    )

    obj_cols = df.select_dtypes(include=['object']).columns.tolist()
    for col in obj_cols:
        if col != 'msno':
            df[col] = pd.to_numeric(df[col], errors='coerce')

    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    df[num_cols] = df[num_cols].fillna(df[num_cols].median())
    return df


# =========================================================
# 8. CatBoost 전용 범주형 유지 버전
# =========================================================
def finalize_catboost_features(df):
    df = df.copy()
    df = df.replace([np.inf, -np.inf], np.nan)

    # CatBoost가 직접 처리할 범주형 컬럼
    cat_cols = ['city', 'registered_via', 'payment_method_id_last', 'gender']
    for col in cat_cols:
        df[col] = df[col].astype('category')

    # 수치형 결측 보정
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    df[num_cols] = df[num_cols].fillna(df[num_cols].median())

    # category 결측 보정
    for col in cat_cols:
        df[col] = df[col].astype(str).fillna('MISSING')

    return df, cat_cols


# =========================================================
# 9. 평가 결과 출력
# =========================================================
def plot_confusion_matrix(y_test, y_pred, title):
    cm = confusion_matrix(y_test, y_pred)
    print(f'혼동행렬:\n{cm}')

    plt.figure(figsize=(8, 6))
    sns.heatmap(
        cm,
        annot=True,
        fmt='d',
        cmap='Blues',
        xticklabels=['Not Churn (0)', 'Churn (1)'],
        yticklabels=['Not Churn (0)', 'Churn (1)']
    )
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.title(title)
    plt.tight_layout()
    plt.show()


def run_xgb_cv(merge_df, merge_df_raw):
    df_model = finalize_numeric_features(merge_df)

    X = df_model.drop(columns=['is_churn', 'msno'], errors='ignore')
    y = df_model['is_churn']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    print(f'CV용 학습 데이터 크기: {X_train.shape}')
    print(f'최종 테스트 데이터 크기: {X_test.shape}')

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    cv_auc_scores = []
    oof_pred = np.zeros(len(X_train))
    test_pred_list = []
    best_iterations = []
    models = []

    X_train_cv = X_train.reset_index(drop=True)
    y_train_cv = y_train.reset_index(drop=True)

    for fold, (tr_idx, val_idx) in enumerate(skf.split(X_train_cv, y_train_cv), 1):
        print(f'\n========== Fold {fold} ==========')

        X_tr = X_train_cv.iloc[tr_idx]
        X_val = X_train_cv.iloc[val_idx]
        y_tr = y_train_cv.iloc[tr_idx]
        y_val = y_train_cv.iloc[val_idx]

        model = XGBClassifier(
            n_estimators=700,
            learning_rate=0.04,
            max_depth=6,
            min_child_weight=3,
            gamma=0.1,
            subsample=0.85,
            colsample_bytree=0.8,
            reg_lambda=4.0,
            reg_alpha=0.5,
            random_state=42,
            eval_metric='logloss',
            early_stopping_rounds=30,
            n_jobs=-1
        )

        model.fit(
            X_tr, y_tr,
            eval_set=[(X_val, y_val)],
            verbose=False
        )

        val_prob = model.predict_proba(X_val)[:, 1]
        val_auc = roc_auc_score(y_val, val_prob)

        oof_pred[val_idx] = val_prob
        cv_auc_scores.append(val_auc)
        test_pred_list.append(model.predict_proba(X_test)[:, 1])
        best_iterations.append(model.best_iteration if hasattr(model, 'best_iteration') else None)
        models.append(model)

        print(f'Fold {fold} AUC: {val_auc:.4f}')
        print(f'Fold {fold} best_iteration: {best_iterations[-1]}')

    print('\n==============================')
    print('CV 결과 요약')
    print('==============================')
    print('Fold별 AUC:', [round(score, 4) for score in cv_auc_scores])
    print(f'Mean CV AUC: {np.mean(cv_auc_scores):.4f}')
    print(f'Std CV AUC : {np.std(cv_auc_scores):.4f}')

    oof_auc = roc_auc_score(y_train_cv, oof_pred)
    print(f'OOF AUC    : {oof_auc:.4f}')

    y_prob = np.mean(test_pred_list, axis=0)
    threshold = 0.4
    y_pred = (y_prob >= threshold).astype(int)

    test_auc = roc_auc_score(y_test, y_prob)
    print(f'\nFinal Test AUC (CV ensemble): {test_auc:.4f}')
    print('--- Classification Report ---')
    print(classification_report(y_test, y_pred))

    # =========================================================
    # 전체 유저 대상 예측 및 저장 (파이프라인 연동용 정규화)
    # =========================================================
    print("📈 전체 유저 풀 스코어링 진행 중 (final_model.csv)...")
    X_full = finalize_numeric_features(merge_df).drop(columns=['is_churn', 'msno'], errors='ignore')
    final_probs = np.mean([m.predict_proba(X_full)[:, 1] for m in models], axis=0)
    
    result_full = pd.DataFrame({
        'msno': merge_df['msno'],
        'churn_probability': final_probs,
        'main_reason_code': '복합적 요인(기타 사유)'
    })
    
    save_path = os.path.join(os.path.dirname(__file__), 'final_model.csv')
    result_full.to_csv(save_path, index=False, encoding='utf-8-sig')
    
    # 분석 및 시뮬레이션을 위한 모델 앙상블 저장 (joblib)
    model_save_path = os.path.join(os.path.dirname(__file__), 'final_model.joblib')
    joblib.dump(models, model_save_path)
    
    print(f"✨ 완료! 통합 파이프라인의 핵심인 {save_path} 와 모델 파일 {model_save_path} 가 생성되었습니다.")

    plot_confusion_matrix(y_test, y_pred, 'Confusion Matrix - XGBoost CV Ensemble')

    importance_values = np.mean([model.feature_importances_ for model in models], axis=0)
    importances = pd.Series(importance_values, index=X_train.columns)
    top20_features = importances.sort_values(ascending=False).head(20)

    plt.figure(figsize=(10, 8))
    plt.title('XGBoost Feature Importances (Top 20, CV Average)', fontsize=15)
    sns.barplot(x=top20_features, y=top20_features.index)
    plt.xlabel('Importance Score')
    plt.ylabel('Features')
    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    merge_df, merge_df_raw = build_modeling_dataframe()
    run_xgb_cv(merge_df, merge_df_raw)