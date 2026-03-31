import os
import pandas as pd
import numpy as np
import xgboost as xgb
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

# ==========================================
# 0. 사유 및 카테고리 매핑 (Reason & Category Mapping)
# ==========================================
REASON_MAP = {
    # 1. 결제 및 구독 (Payment & Subscription)
    'is_auto_renew': '자동 결제 해지 또는 미설정',
    'is_cancel': '직접적인 서비스 취소 요청 발생',
    'payment_plan_days': '결제 플랜 기간 (단기 이용 등)',
    'actual_amount_paid': '실제 결제 금액 관련 특이점',
    'plan_list_price': '플랜 가격 관련 요인',
    'trans_count': '결제 및 갱신 횟수 부족',
    'payment_method_id': '특정 결제 수단 이용 특성',

    # 2. 활동 및 참여 (Activity & Engagement)
    'active_days': '월간 활동 빈도 저조',
    'total_secs': '전체 스트리밍 시간 부족',
    'tenure': '서비스 가입 기간(장기/단기) 특성',
    'num_25': '25% 이하 청취 비중 높음',
    'num_50': '50% 이하 청취 비중 높음',
    'num_75': '75% 이하 청취 비중 높음',
    'num_985': '98.5% 이하 청취 비중 높음',
    'num_100': '100% 완청 횟수 낮음',

    # 3. 콘텐츠 이용 습관 (Content Habits)
    'completion_ratio': '음악 완청 비율 저조 (관심도 하락)',
    'unique_ratio': '음악 청취 다양성 부족',
    'total_songs': '전체 스트리밍 곡 수 부족',

    # 4. 사용자 프로필 (Demographics)
    'city': '지역적 인구 통계 특성',
    'registered_via': '특정 가입 경로(플랫폼) 특성',
    'bd': '사용자 연령대 특성',
    'gender': '성별 관련 가입 특성',

    'None': '기타 요인 또는 사유 없음'
}

CATEGORY_MAP = {
    'is_auto_renew': '결제 및 구독', 'is_cancel': '결제 및 구독', 'payment_plan_days': '결제 및 구독',
    'actual_amount_paid': '결제 및 구독', 'plan_list_price': '결제 및 구독', 'trans_count': '결제 및 구독',
    'payment_method_id': '결제 및 구독',
    'active_days': '활동 및 참여', 'total_secs': '활동 및 참여', 'tenure': '활동 및 참여',
    'num_25': '활동 및 참여', 'num_50': '활동 및 참여', 'num_75': '활동 및 참여',
    'num_985': '활동 및 참여', 'num_100': '활동 및 참여',
    'completion_ratio': '콘텐츠 이용 습관', 'unique_ratio': '콘텐츠 이용 습관', 'total_songs': '콘텐츠 이용 습관',
    'city': '사용자 프로필', 'registered_via': '사용자 프로필', 'bd': '사용자 프로필',
    'gender': '사용자 프로필',
    'None': '기타'
}

def get_base_feature_name(col):
    """OHE 컬럼 등에서 베이스 피처 이름을 추출합니다."""
    for base in REASON_MAP.keys():
        if col.startswith(f"{base}_") or col == base:
            return base
    return col

# ==========================================
# 1. 데이터 로더 & 전처리 (936model 기준)
# ==========================================
def load_and_preprocess_936():
    """
    936ml.py의 로직을 따라 데이터를 로드하고 전처리합니다.
    """
    print("📦 [936 설정] 데이터 로드 중...")
    BASE_PATH = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'raw')
    
    train_members = pd.read_csv(os.path.join(BASE_PATH, 'train_members_v2.csv'))
    transactions = pd.read_csv(os.path.join(BASE_PATH, 'transactions_v2.csv'))
    user_logs = pd.read_csv(os.path.join(BASE_PATH, 'user_logs_aug_v2.csv'))

    # 중복 제거
    train_members = train_members.drop_duplicates(subset=['msno'], keep='first')
    transactions = transactions.drop_duplicates()
    user_logs = user_logs.drop_duplicates()

    # gender 및 범주형 변환
    train_members['gender'] = train_members['gender'].map({'female': 0, 'male': 1})
    
    # 날짜 및 집계
    train_members['registration_init_time'] = pd.to_datetime(train_members['registration_init_time'])
    transactions['transaction_date'] = pd.to_datetime(transactions['transaction_date'], format='%Y-%m-%d')
    
    # 연령대 중앙값 처리
    median_age = train_members[(train_members['bd'] > 0) & (train_members['bd'] < 100)]['bd'].median()
    train_members.loc[(train_members['bd'] <= 0) | (train_members['bd'] >= 100), 'bd'] = median_age

    # transactions 집계
    transactions = transactions.sort_values(by=['msno', 'transaction_date'])
    trans_features = transactions.groupby('msno').agg({
        'payment_method_id': 'last',
        'payment_plan_days': 'mean',
        'plan_list_price': 'mean',
        'actual_amount_paid': 'mean',
        'is_auto_renew': 'last',
        'is_cancel': 'last',
        'transaction_date': 'count'
    }).reset_index()
    trans_features.rename(columns={'transaction_date': 'trans_count'}, inplace=True)

    # user_logs 집계
    if 'date' in user_logs.columns:
        user_logs['date'] = pd.to_datetime(user_logs['date'], format='%Y%m%d')
        log_features = user_logs.groupby('msno').agg({
            'date': 'count', 'num_25': 'sum', 'num_50': 'sum', 'num_75': 'sum',
            'num_985': 'sum', 'num_100': 'sum', 'num_unq': 'sum', 'total_secs': 'sum'
        }).reset_index()
        log_features.rename(columns={'date': 'active_days'}, inplace=True)
    else:
        log_features = user_logs.copy()

    log_features['total_songs'] = log_features[['num_25', 'num_50', 'num_75', 'num_985', 'num_100']].sum(axis=1)
    log_features['completion_ratio'] = log_features['num_100'] / (log_features['total_songs'] + 1e-9)
    log_features['unique_ratio'] = log_features['num_unq'] / (log_features['total_songs'] + 1e-9)

    # 병합
    merge_df = train_members.merge(trans_features, on='msno', how='left')
    merge_df = merge_df.merge(log_features, on='msno', how='left')

    # tenure 계산 (가입 기간)
    ref_date = merge_df['registration_init_time'].max()
    merge_df['tenure'] = (ref_date - merge_df['registration_init_time']).dt.days
    
    return merge_df

# ==========================================
# 2. 학습 및 상세 분석
# ==========================================
def train_and_explain_936(df):
    """
    936ml.py의 모델 하이퍼파라미터를 사용하여 학습하고 사유를 추출합니다.
    """
    user_id_series = df['msno']
    is_churn_series = df['is_churn']
    
    # 불필요 컬럼 제거 및 OHE
    X_raw = df.drop(['msno', 'is_churn', 'registration_init_time'], axis=1)
    X = pd.get_dummies(X_raw, columns=['city', 'registered_via', 'payment_method_id', 'gender'], drop_first=True)
    X = X.fillna(0)
    y = is_churn_series

    # 훈련/테스트 분할
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # 클래스 불균형 비율
    ratio = float(y_train.value_counts()[0] / y_train.value_counts()[1])

    # 936 모델 하이퍼파라미터
    model = XGBClassifier(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=3,
        scale_pos_weight=ratio,
        random_state=42,
        use_label_encoder=False,
        eval_metric='logloss'
    )

    print("🚀 [936 설정] XGBoost 모델 학습 중...")
    model.fit(X_train, y_train)
    
    auc = roc_auc_score(y_val, model.predict_proba(X_val)[:, 1])
    print(f"✅ 테스트 AUC Score: {auc:.4f}")

    # 상세 사유 추출
    print("🔍 상세 사유 분석 중...")
    contribs = model.get_booster().predict(xgb.DMatrix(X), pred_contribs=True)
    feature_names = X.columns.tolist()

    reasons_list = []
    for i in range(len(contribs)):
        # 기여도가 큰 상위 3개 지표
        user_contrib = contribs[i, :-1]
        sorted_indices = np.argsort(user_contrib)[::-1]
        
        user_reasons = []
        for idx in sorted_indices[:3]:
            if user_contrib[idx] > 0:
                base_name = get_base_feature_name(feature_names[idx])
                user_reasons.append(base_name)
            else:
                user_reasons.append("None")
        while len(user_reasons) < 3: user_reasons.append("None")
        reasons_list.append(user_reasons)

    analysis_df = pd.DataFrame({
        'msno': user_id_series,
        'churn_probability': model.predict_proba(X)[:, 1].round(4)
    })
    
    raw_reasons = pd.DataFrame(reasons_list, columns=['reason_1', 'reason_2', 'reason_3'])
    reasons_df = pd.DataFrame(index=raw_reasons.index)
    
    # 한글 매핑
    for i in range(1, 4):
        col = f'reason_{i}'
        reasons_df[col] = raw_reasons[col].map(REASON_MAP).fillna(raw_reasons[col])
        reasons_df[f'category_{i}'] = raw_reasons[col].map(CATEGORY_MAP).fillna('기타')

    final_output = pd.concat([analysis_df, reasons_df], axis=1)
    return final_output

# ==========================================
# 3. 메인 실행
# ==========================================
if __name__ == "__main__":
    try:
        # 데이터 전처리
        master_df = load_and_preprocess_936()
        
        # 학습 및 결과 도출
        result_csv = train_and_explain_936(master_df)
        
        # 파일 저장 (936model.csv)
        OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '936mlmodel.csv')
        result_csv.to_csv(OUTPUT_FILE, index=False)
        
        print(f"\n✨ [완료] 분석 결과가 저장되었습니다: {OUTPUT_FILE}")
    except Exception as e:
        import traceback
        print("\n❌ [에러 발생]")
        traceback.print_exc()