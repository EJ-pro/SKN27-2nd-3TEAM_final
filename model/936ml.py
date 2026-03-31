import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix

# 데이터 경로 정의
BASE_PATH = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'raw')

# 파일 로드
print("📦 데이터 로드 중...")
train_members = pd.read_csv(os.path.join(BASE_PATH, 'train_members_v2.csv'))
transactions = pd.read_csv(os.path.join(BASE_PATH, 'transactions_v2.csv'))
user_logs = pd.read_csv(os.path.join(BASE_PATH, 'user_logs_aug_v2.csv'))

# 중복 제거
train_members = train_members.drop_duplicates(subset=['msno'], keep='first')
transactions = transactions.drop_duplicates()
user_logs = user_logs.drop_duplicates()

# gender 변환
train_members['gender'] = train_members['gender'].map({'female': 0, 'male': 1})

# 범주형 타입 변환
cat_cols = ['city', 'registered_via']
for col in cat_cols:
    train_members[col] = train_members[col].astype('category')

# 날짜 데이터 변환
train_members['registration_init_time'] = pd.to_datetime(train_members['registration_init_time'])
transactions['transaction_date'] = pd.to_datetime(transactions['transaction_date'], format='%Y-%m-%d')
transactions['membership_expire_date'] = pd.to_datetime(transactions['membership_expire_date'], format='%Y-%m-%d')

# 0세 이하 또는 100세 이상의 값을 중앙값으로 대체
median_age = train_members[(train_members['bd'] > 0) & (train_members['bd'] < 100)]['bd'].median()
train_members.loc[(train_members['bd'] <= 0) | (train_members['bd'] >= 100), 'bd'] = median_age

# transactions 그룹화 및 요약
transactions = transactions.sort_values(by=['msno', 'transaction_date'])
transactions_features = transactions.groupby('msno').agg({
    'payment_method_id': 'last',
    'payment_plan_days': 'mean',
    'plan_list_price': 'mean',
    'actual_amount_paid': 'mean',
    'is_auto_renew': 'last',
    'is_cancel': 'last',
    'transaction_date': 'count'
}).reset_index()
transactions_features.rename(columns={'transaction_date': 'trans_count'}, inplace=True)

# user_logs 집계 데이터 생성
if 'date' in user_logs.columns:
    user_logs['date'] = pd.to_datetime(user_logs['date'], format='%Y%m%d')
    log_features = user_logs.groupby('msno').agg({
        'date': 'count',
        'num_25': 'sum',
        'num_50': 'sum',
        'num_75': 'sum',
        'num_985': 'sum',
        'num_100': 'sum',
        'num_unq': 'sum',
        'total_secs': 'sum'
    }).reset_index()
    log_features.rename(columns={'date': 'active_days'}, inplace=True)
else:
    # 이미 집계된 상태라면 그대로 사용
    print("ℹ️ user_logs가 이미 집계된 상태입니다. 그대로 사용합니다.")
    log_features = user_logs.copy()
    if 'active_days' not in log_features.columns:
        # 활동 일수 정보가 없다면 최소 1일로 가정하거나 0으로 둡니다.
        log_features['active_days'] = 0 

log_features['total_songs'] = log_features[['num_25', 'num_50', 'num_75', 'num_985', 'num_100']].sum(axis=1)
log_features['completion_ratio'] = log_features['num_100'] / (log_features['total_songs'] + 1e-9)
log_features['unique_ratio'] = log_features['num_unq'] / (log_features['total_songs'] + 1e-9)
log_features.rename(columns={'date': 'active_days'}, inplace=True)

# 데이터 병합
print("🔗 데이터 병합 중...")
merge_df = train_members.merge(transactions_features, on='msno', how='left')
merge_df = merge_df.merge(log_features, on='msno', how='left')

# ID 보관 및 처리
user_id_series = merge_df['msno']
is_churn_series = merge_df['is_churn']
merge_df_cleaned = merge_df.drop(['msno', 'is_churn'], axis=1)

# 전처리 (날짜 수치화)
ref_date = merge_df_cleaned['registration_init_time'].max()
merge_df_cleaned['tenure'] = (ref_date - merge_df_cleaned['registration_init_time']).dt.days
merge_df_cleaned = merge_df_cleaned.drop('registration_init_time', axis=1)

# 원핫 인코딩
merge_df_encoded = pd.get_dummies(merge_df_cleaned, columns=['city', 'registered_via', 'payment_method_id', 'gender'], drop_first=True)

# 결측치 처리 (간단하게 0으로 채움)
merge_df_encoded = merge_df_encoded.fillna(0)

# 최종 학습용 데이터셋 준비
X = merge_df_encoded
y = is_churn_series

# 훈련/테스트 분할
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

print("🚀 모델 학습 중...")
# 클래스 불균형 계산
ratio = float(y_train.value_counts()[0] / y_train.value_counts()[1])

# 모델 생성 (XGBoost)
xgb_model = XGBClassifier(
    n_estimators=100,
    learning_rate=0.1,
    max_depth=3,
    scale_pos_weight=ratio,
    random_state=42,
    use_label_encoder=False,
    eval_metric='logloss'
)

# 모델 학습
xgb_model.fit(X_train, y_train)

# 결과 출력
test_probs = xgb_model.predict_proba(X_test)[:, 1]
print(f"✅ 테스트 AUC Score: {roc_auc_score(y_test, test_probs):.4f}")

# 🔥 최종 결과 저장 (936model.csv)
print("💾 결과 저장 중 (936model.csv)...")
full_probs = xgb_model.predict_proba(X)[:, 1]
output_df = pd.DataFrame({
    'msno': user_id_series,
    'churn_probability': full_probs
})

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '936model.csv')
output_df.to_csv(OUTPUT_FILE, index=False)
print(f"✨ 완료! 결과가 {OUTPUT_FILE}에 저장되었습니다.")

# 시각화 (중요도)
plt.figure(figsize=(10, 8))
plt.title('XGBoost Feature Importances', fontsize=15)
importances = pd.Series(xgb_model.feature_importances_, index=X.columns)
top20 = importances.sort_values(ascending=False).head(20)
sns.barplot(x=top20, y=top20.index, palette='viridis')
plt.xlabel('Importance Score')
plt.tight_layout()
plt.savefig(os.path.join(os.path.dirname(__file__), 'feature_importance.png'))
print("📊 중요도 그래프가 feature_importance.png로 저장되었습니다.")
# plt.show() # 로컬 환경에 따라 주석 처리 가능