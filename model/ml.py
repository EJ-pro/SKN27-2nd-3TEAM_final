import os
import sys
import pandas as pd
import numpy as np
import xgboost as xgb
import polars as pl
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
    'transaction_count': '결제 및 갱신 횟수 부족',

    # 2. 활동 및 참여 (Activity & Engagement)
    'recency': '최근 접속일로부터 장기간 미접속',
    'last_week_secs': '최근 일주일간 청취 시간 급감',
    'active_days': '월간 로그인 및 활동 빈도 저조',
    'total_secs': '전체 스트리밍 시간 부족',
    'log_count': '전반적인 활동 횟수 부족',
    'usage_trend': '활동량 변화 트렌드 (지속적 감소세)',

    # 3. 콘텐츠 이용 습관 (Content Habits)
    'completion_rate': '음악 완청 비율 저조 (관심도 하락)',
    'unique_ratio': '음악 청취 다양성 부족',

    # 4. 사용자 프로필 (Demographics)
    'city': '지역적 인구 통계 특성',
    'registered_via': '특정 가입 경로(플랫폼) 특성',
    'bd': '사용자 연령대 특성',
    'registration_init_time': '가입 기간(최근 가입 등) 특성',

    'None': '기타 요인 또는 사유 없음'
}

CATEGORY_MAP = {
    'is_auto_renew': '결제 및 구독', 'is_cancel': '결제 및 구독', 'payment_plan_days': '결제 및 구독',
    'actual_amount_paid': '결제 및 구독', 'plan_list_price': '결제 및 구독', 'transaction_count': '결제 및 구독',
    'recency': '활동 및 참여', 'last_week_secs': '활동 및 참여', 'active_days': '활동 및 참여',
    'total_secs': '활동 및 참여', 'log_count': '활동 및 참여', 'usage_trend': '활동 및 참여',
    'completion_rate': '콘텐츠 이용 습관', 'unique_ratio': '콘텐츠 이용 습관',
    'city': '사용자 프로필', 'registered_via': '사용자 프로필', 'bd': '사용자 프로필',
    'registration_init_time': '사용자 프로필',
    'None': '기타'
}

# ==========================================
# 1. 데이터 로더 (Data Loader)
# ==========================================
def load_data(data_dir="data/processed"):
    """
    구성원, 거래 내역, 유저 로그 데이터를 로드합니다.
    """
    print("데이터셋을 로드하는 중...")
    
    # 공통 컬럼 정리 함수 (Windows CSV 특수문자 \r 제거)
    def clean_columns(df):
        if df is not None:
            df.columns = [c.strip() for c in df.columns]
        return df

    # 작은 데이터는 Pandas로 로드
    try:
        members = clean_columns(pd.read_csv(os.path.join(data_dir, "train_members.csv")))
        transactions = clean_columns(pd.read_csv(os.path.join(data_dir, "transactions.csv")))
    except FileNotFoundError as e:
        print(f"파일을 찾을 수 없습니다: {e}")
        return None, None, None
        
    # 대용량 유저 로그는 Polars로 빠르게 로드
    try:
        logs = pl.read_csv(os.path.join(data_dir, "user_logs.csv"))
        logs.columns = [c.strip() for c in logs.columns]
        logs = logs.to_pandas()
    except Exception as e:
        print(f"Polars 로드 실패, Pandas로 전환합니다. 에러: {e}")
        try:
            logs = clean_columns(pd.read_csv(os.path.join(data_dir, "user_logs.csv")))
        except FileNotFoundError:
            logs = None
            
    print("데이터 로드 완료.")
    return members, transactions, logs

# ==========================================
# 2. 전처리 (Preprocessing)
# ==========================================
def preprocess_data(members, transactions, logs):
    """
    데이터 타입 변환 및 결측치 처리를 수행합니다.
    """
    print("데이터 전처리 중...")
    
    # 로그 데이터 수치화 (stray characters 처리)
    numeric_cols = ['num_25', 'num_50', 'num_75', 'num_985', 'num_100', 'num_unq', 'total_secs']
    for col in numeric_cols:
        if col in logs.columns:
            logs[col] = pd.to_numeric(logs[col], errors='coerce').fillna(0)
    
    # 멤버 데이터 전처리
    if 'registration_init_time' in members.columns:
        members['registration_init_time'] = pd.to_datetime(members['registration_init_time'], format='%Y%m%d', errors='coerce')
    
    # 거래 데이터 전처리
    if 'transaction_date' in transactions.columns:
        transactions['transaction_date'] = pd.to_datetime(transactions['transaction_date'], format='%Y%m%d', errors='coerce')
        
    return members, transactions, logs

# ==========================================
# 3. 특성 공학 (Feature Engineering)
# ==========================================
def extract_features(members, transactions, logs, snapshot_date='2017-03-01'):
    """
    행동 지표(로그), 거래 패턴 등을 분석하여 학습용 피처를 생성합니다.
    """
    print("피처 엔지니어링 수행 중...")
    snap_dt = pd.to_datetime(snapshot_date)
    
    # 3.1 거래 피처 추출
    trans_features = transactions.sort_values(by=['msno', 'transaction_date'])
    trans_agg = trans_features.groupby('msno').agg({
        'payment_plan_days': 'mean',
        'plan_list_price': 'mean',
        'actual_amount_paid': 'mean',
        'is_auto_renew': 'last',
        'is_cancel': 'sum',
        'transaction_date': 'count'
    }).reset_index()
    trans_agg.rename(columns={'transaction_date': 'transaction_count'}, inplace=True)
    
    # 3.2 로그 피처 추출 (최근성, 트렌드 포함)
    logs['date'] = pd.to_datetime(logs['date'], format='%Y%m%d', errors='coerce')
    log_agg = logs.groupby('msno').agg({
        'num_25': 'sum', 'num_50': 'sum', 'num_75': 'sum', 'num_985': 'sum', 'num_100': 'sum',
        'num_unq': 'sum', 'total_secs': 'sum',
        'date': ['max', 'nunique']
    })
    log_agg.columns = ['sum_25', 'sum_50', 'sum_75', 'sum_985', 'sum_100', 'sum_unq', 'total_secs', 'last_date', 'active_days']
    log_agg = log_agg.reset_index()
    
    # 최근성(Recency): 마지막 활동일로부터의 경과일
    log_agg['recency'] = (snap_dt - log_agg['last_date']).dt.days
    
    # 완청율: 전체 중 100% 다 들은 비율
    total_songs = log_agg[['sum_25', 'sum_50', 'sum_75', 'sum_985', 'sum_100']].sum(axis=1)
    log_agg['completion_rate'] = np.where(total_songs > 0, log_agg['sum_100'] / total_songs, 0)
    
    # 트렌드: 2월 마지막 주 활동량 vs 전체 평균 대비 주간 활동량
    last_week_dt = snap_dt - pd.Timedelta(days=7)
    last_week_logs = logs[logs['date'] >= last_week_dt]
    last_week_agg = last_week_logs.groupby('msno')['total_secs'].sum().reset_index()
    last_week_agg.rename(columns={'total_secs': 'last_week_secs'}, inplace=True)
    
    log_agg = pd.merge(log_agg, last_week_agg, on='msno', how='left').fillna(0)
    log_agg['usage_trend'] = np.where(log_agg['total_secs'] > 0, 
                                     log_agg['last_week_secs'] / (log_agg['total_secs'] / 4), 0)
    
    # 3.3 통합 데이터셋 생성
    master = pd.merge(members, trans_agg, on='msno', how='left')
    master = pd.merge(master, log_agg, on='msno', how='left')
    master.fillna(0, inplace=True)
    
    return master

# ==========================================
# 4. 모델 학습 및 개인별 사유 추출
# ==========================================
def train_and_explain(df):
    """
    XGBoost 모델을 학습시키고 각 사용자별 이탈 사유를 분석합니다.
    """
    # 타겟 분리 (데이터에 이탈 여부가 없을 경우 랜덤 생성 - 테스트용)
    if 'is_churn' not in df.columns:
        print("경고: 'is_churn' 컬럼이 없어 임의의 라벨을 생성합니다.")
        df['is_churn'] = np.random.randint(0, 2, size=len(df))
        
    drop_cols = ['msno', 'is_churn', 'registration_init_time', 'last_date', 'gender']
    X = df.drop(columns=[c for c in drop_cols if c in df.columns])
    y = df['is_churn']
    
    # 범주형 타입 명시
    for col in ['city', 'registered_via']:
        if col in X.columns:
            X[col] = X[col].astype('category')
            
    # 학습/검증 분할
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # 모델 정의
    model = xgb.XGBClassifier(
        n_estimators=300, learning_rate=0.05, max_depth=6, 
        enable_categorical=True, n_jobs=-1, random_state=42, verbosity=0
    )
    
    print("XGBoost 모델 학습 중...")
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    
    print(f"모델 성능 (AUC): {roc_auc_score(y_val, model.predict_proba(X_val)[:, 1]):.4f}")
    
    # 개인별 기여도 추출 (XGBoost Internal SHAP)
    print("개인별 이탈 사유 생성 중 (약 30초~1분 소요)...")
    contribs = model.get_booster().predict(xgb.DMatrix(X, enable_categorical=True), pred_contribs=True)
    feature_names = X.columns.tolist()
    
    reasons = []
    for i in range(len(contribs)):
        # 기여도가 큰 상위 3개 지표 (이탈을 부추기는 요인)
        user_contrib = contribs[i, :-1]
        sorted_indices = np.argsort(user_contrib)[::-1]
        
        user_reasons = []
        for idx in sorted_indices[:3]:
            if user_contrib[idx] > 0: user_reasons.append(feature_names[idx])
            else: user_reasons.append("None")
        while len(user_reasons) < 3: user_reasons.append("None")
        reasons.append(user_reasons)
        
    analysis_df = pd.DataFrame({
        'msno': df['msno'],
        'churn_probability': model.predict_proba(X)[:, 1].round(4)
    })
    raw_reasons = pd.DataFrame(reasons, columns=['reason_1', 'reason_2', 'reason_3'])
    reasons_df = pd.DataFrame(index=raw_reasons.index)
    
    # 한글로 변환 (REASON_MAP / CATEGORY_MAP 적용)
    reasons_df['reason_1'] = raw_reasons['reason_1'].map(REASON_MAP).fillna(raw_reasons['reason_1'])
    reasons_df['reason_2'] = raw_reasons['reason_2'].map(REASON_MAP).fillna(raw_reasons['reason_2'])
    reasons_df['reason_3'] = raw_reasons['reason_3'].map(REASON_MAP).fillna(raw_reasons['reason_3'])
    
    reasons_df['category_1'] = raw_reasons['reason_1'].map(CATEGORY_MAP).fillna('기타')
    reasons_df['category_2'] = raw_reasons['reason_2'].map(CATEGORY_MAP).fillna('기타')
    reasons_df['category_3'] = raw_reasons['reason_3'].map(CATEGORY_MAP).fillna('기타')
    
    final_output = pd.concat([analysis_df, reasons_df], axis=1)
    
    return final_output, model

# ==========================================
# 5. 메인 실행 (Main)
# ==========================================
if __name__ == "__main__":
    # 데이터 경로 및 설정
    DATA_PATH = "data/processed"
    OUTPUT_FILE = "data/processed/user_churn_analysis_final.csv"
    
    # 1단계: 로드
    members, transactions, logs = load_data(DATA_PATH)
    
    if members is not None:
        # 2단계: 전처리
        members, transactions, logs = preprocess_data(members, transactions, logs)
        
        # 3단계: 특성 추출
        master_df = extract_features(members, transactions, logs)
        
        # 4단계: 학습 및 사유 분석
        result_csv, model = train_and_explain(master_df)
        
        # 5단계: 결과 저장
        result_csv.to_csv(OUTPUT_FILE, index=False)
        print(f"\n[완료] 모든 분석 결과가 저장되었습니다: {OUTPUT_FILE}")
        
        # 중요 변수 요약 출력
        importance = pd.DataFrame({
            'feature': list(model.get_booster().get_score(importance_type='gain').keys()),
            'importance': list(model.get_booster().get_score(importance_type='gain').values())
        }).sort_values(by='importance', ascending=False)
        print("\n=== 글로벌 이탈 영향 지표 TOP 5 ===")
        print(importance.head(5))