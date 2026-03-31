import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score

# -------------------------------------------------
# 공통 유틸 함수
# -------------------------------------------------
def to_datetime_maybe_yyyymmdd(s: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(s):
        return pd.to_datetime(s, errors="coerce")
    s = s.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    if s.str.fullmatch(r"\d{8}").all():
        return pd.to_datetime(s, format="%Y%m%d", errors="coerce")
    return pd.to_datetime(s, errors="coerce")

def safe_div(num: pd.Series, den: pd.Series) -> pd.Series:
    den = den.replace(0, np.nan)
    out = (num / den).replace([np.inf, -np.inf], np.nan)
    return out.fillna(0)

# 1. 데이터 로드 및 기준일 생성
def build_feature_table(train_members, transactions, user_logs):
    print("🔧 데이터 전처리 및 피처 생성 중...")
    
    # 1-1. 기준일 (snapshot_date) 설정
    transactions['transaction_date'] = to_datetime_maybe_yyyymmdd(transactions['transaction_date'])
    transactions['membership_expire_date'] = to_datetime_maybe_yyyymmdd(transactions['membership_expire_date'])
    
    snapshot_df = transactions.sort_values(['msno', 'transaction_date', 'membership_expire_date']).groupby('msno').tail(1)[['msno', 'membership_expire_date']]
    snapshot_df.rename(columns={'membership_expire_date': 'snapshot_date'}, inplace=True)
    
    train_members = train_members.merge(snapshot_df, on='msno', how='left')
    train_members['registration_init_time'] = to_datetime_maybe_yyyymmdd(train_members['registration_init_time'])
    
    # 1-2. members 피처
    members_feat = train_members.copy()
    members_feat['gender'] = members_feat['gender'].map({'female': 0, 'male': 1}).fillna(-1)
    members_feat['account_age_days'] = (members_feat['snapshot_date'] - members_feat['registration_init_time']).dt.days.fillna(0)
    
    median_age = members_feat[(members_feat['bd'] > 0) & (members_feat['bd'] < 100)]['bd'].median()
    members_feat['bd'] = members_feat['bd'].apply(lambda x: x if 0 < x < 100 else median_age)
    
    # 1-3. transactions 피처
    tx_agg = transactions.groupby('msno').agg({
        'payment_method_id': 'last',
        'payment_plan_days': ['mean', 'last'],
        'plan_list_price': 'mean',
        'actual_amount_paid': 'mean',
        'is_auto_renew': 'last',
        'is_cancel': 'last',
        'transaction_date': 'count'
    }).reset_index()
    tx_agg.columns = ['msno', 'last_payment_method', 'plan_days_mean', 'last_plan_days', 'plan_price_mean', 'paid_mean', 'last_auto_renew', 'last_cancel', 'tx_count']
    
    # 1-4. user_logs 피처 (V2 버전은 이미 집계된 상태)
    log_feat = user_logs.copy()
    log_feat['play_total'] = log_feat[['num_25', 'num_50', 'num_75', 'num_985', 'num_100']].sum(axis=1)
    log_feat['completion_ratio'] = log_feat['num_100'] / (log_feat['play_total'] + 1e-9)
    log_feat['skip_ratio'] = log_feat['num_25'] / (log_feat['play_total'] + 1e-9)
    
    # 1-5. 데이터 병합
    final_df = members_feat.merge(tx_agg, on='msno', how='left')
    final_df = final_df.merge(log_feat, on='msno', how='left')
    
    # 불필요 컬럼 제거 및 인코딩
    user_ids = final_df['msno']
    y = final_df['is_churn']
    X = final_df.drop(['msno', 'is_churn', 'registration_init_time', 'snapshot_date'], axis=1)
    X = pd.get_dummies(X, columns=['city', 'registered_via', 'last_payment_method'], drop_first=True)
    X = X.fillna(0)
    
    return X, y, user_ids

if __name__ == "__main__":
    BASE_PATH = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'raw')
    
    print("📦 데이터 로드 중...")
    train_members_raw = pd.read_csv(os.path.join(BASE_PATH, 'train_members_v2.csv'))
    transactions_raw = pd.read_csv(os.path.join(BASE_PATH, 'transactions_v2.csv'))
    user_logs_raw = pd.read_csv(os.path.join(BASE_PATH, 'user_logs_aug_v2.csv'))
    
    X, y, user_ids = build_feature_table(train_members_raw, transactions_raw, user_logs_raw)
    
    # 훈련/테스트 분할
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print("🚀 모델 학습 중 (980ml - Premium Edition)...")
    # 고급 학습 설정
    clf = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=float(len(y_train[y_train==0]) / len(y_train[y_train==1])),
        eval_metric='logloss'
    )
    clf.fit(X_train, y_train)
    
    # 결과 출력
    probs = clf.predict_proba(X_test)[:, 1]
    print(f"✅ 테스트 AUC Score: {roc_auc_score(y_test, probs):.4f}")
    
    # 결과 저장
    print("💾 결과 저장 중 (980model.csv)...")
    full_probs = clf.predict_proba(X)[:, 1]
    output_df = pd.DataFrame({
        'msno': user_ids,
        'churn_probability': full_probs
    })
    
    OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '980model.csv')
    output_df.to_csv(OUTPUT_FILE, index=False)
    print(f"✨ 완료! 결과가 {OUTPUT_FILE}에 저장되었습니다.")
    
    # 중요도 시각화
    plt.figure(figsize=(12, 10))
    importances = pd.Series(clf.feature_importances_, index=X.columns)
    top20 = importances.sort_values(ascending=False).head(20)
    sns.barplot(x=top20, y=top20.index, palette='magma')
    plt.title('XGBoost Feature Importances (980 Model)', fontsize=15)
    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), 'feature_importance_980.png'))
    print("📊 중요도 그래프가 feature_importance_980.png로 저장되었습니다.")