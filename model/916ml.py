import os
import pandas as pd
import numpy as np
import torch
from torch import nn, optim
from torch.utils.data import TensorDataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score

# 데이터 경로 정의
BASE_PATH = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'raw')

# 1. 데이터 로드
print("📦 데이터 로드 중...")
train_members = pd.read_csv(os.path.join(BASE_PATH, 'train_members_v2.csv'))
transactions = pd.read_csv(os.path.join(BASE_PATH, 'transactions_v2.csv'))
user_logs = pd.read_csv(os.path.join(BASE_PATH, 'user_logs_aug_v2.csv'))

# 중복 제거
train_members = train_members.drop_duplicates(subset=['msno'], keep='first')
transactions = transactions.drop_duplicates()
user_logs = user_logs.drop_duplicates()

# 2. 전처리
print("🔧 데이터 전처리 및 피처 엔지니어링 중...")
train_members['gender'] = train_members['gender'].map({'female': 0, 'male': 1}).fillna(-1)

# 날짜 변환 및 수치화
train_members['registration_init_time'] = pd.to_datetime(train_members['registration_init_time'], errors='coerce')
ref_date = train_members['registration_init_time'].max()
train_members['tenure'] = (ref_date - train_members['registration_init_time']).dt.days.fillna(0)

# 0세 이하 또는 100세 이상의 값을 중앙값으로 대체
median_age = train_members[(train_members['bd'] > 0) & (train_members['bd'] < 100)]['bd'].median()
train_members['bd'] = train_members['bd'].apply(lambda x: x if 0 < x < 100 else median_age)

# transactions 요약
transactions['transaction_date'] = pd.to_datetime(transactions['transaction_date'], errors='coerce')
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

# user_logs (이미 집계된 상태인 v2 버전 처리)
log_features = user_logs.copy()
log_features['total_songs'] = log_features[['num_25', 'num_50', 'num_75', 'num_985', 'num_100']].sum(axis=1)
log_features['completion_ratio'] = log_features['num_100'] / (log_features['total_songs'] + 1e-9)
log_features['unique_ratio'] = log_features['num_unq'] / (log_features['total_songs'] + 1e-9)

# 3. 데이터 합치기
print("🔗 데이터 병합 중...")
merge_df = train_members.merge(trans_features, on='msno', how='left')
merge_df = merge_df.merge(log_features, on='msno', how='left')

# ID 및 타겟 분리
user_id_series = merge_df['msno']
y = merge_df['is_churn'].values
X_raw = merge_df.drop(['msno', 'is_churn', 'registration_init_time'], axis=1)

# 범주형 인코딩 (One-hot)
X_encoded = pd.get_dummies(X_raw, columns=['city', 'registered_via', 'payment_method_id', 'gender'], drop_first=True)
X_encoded = X_encoded.fillna(0).astype(np.float32)

# 스케일링 (신경망은 스케일링이 중요합니다)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_encoded)

# 4. 텐서 준비 및 학습
print("🚀 PyTorch 데이터셋 구성 중...")
device = 'cuda' if torch.cuda.is_available() else 'cpu'

X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.15, random_state=42, stratify=y)

X_train_t = torch.tensor(X_train, dtype=torch.float32)
y_train_t = torch.tensor(y_train, dtype=torch.long)
X_test_t = torch.tensor(X_test, dtype=torch.float32)
y_test_t = torch.tensor(y_test, dtype=torch.long)

train_loader = DataLoader(TensorDataset(X_train_t, y_train_t), batch_size=64, shuffle=True)
test_loader = DataLoader(TensorDataset(X_test_t, y_test_t), batch_size=64, shuffle=False)

# 5. 모델 정의 (FCModel)
class FCModel(nn.Module):
    def __init__(self, feature_size, target_size, hidden_size=128):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(feature_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, target_size)
        )

    def forward(self, x):
        return self.layers(x)

feature_size = X_train.shape[1]
model = FCModel(feature_size, 2).to(device)
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# 6. 학습 루프
print(f"⌛ 학습 시작 (Device: {device})...")
num_epochs = 10
for epoch in range(num_epochs):
    model.train()
    total_loss = 0
    for inputs, labels in train_loader:
        inputs, labels = inputs.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    print(f"Epoch [{epoch+1}/{num_epochs}] Loss: {total_loss/len(train_loader):.4f}")

# 7. 평가 및 결과 저장
print("⚖️ 모델 평가 및 결과 저장 중...")
model.eval()
with torch.no_grad():
    all_inputs = torch.tensor(X_scaled, dtype=torch.float32).to(device)
    raw_outputs = model(all_inputs)
    probs = torch.softmax(raw_outputs, dim=1)[:, 1].cpu().numpy()

output_df = pd.DataFrame({
    'msno': user_id_series,
    'churn_probability': probs
})

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '916model.csv')
output_df.to_csv(OUTPUT_FILE, index=False)
print(f"✨ 완료! 결과가 {OUTPUT_FILE}에 저장되었습니다.")

# 테스트 데이터 지표 출력
with torch.no_grad():
    y_test_pred = model(X_test_t.to(device))
    y_test_probs = torch.softmax(y_test_pred, dim=1)[:, 1].cpu().numpy()
    print(f"✅ 테스트 AUC Score: {roc_auc_score(y_test, y_test_probs):.4f}")