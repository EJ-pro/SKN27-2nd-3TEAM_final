import os
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

# -------------------------------------------------
# 1. Path & Data Load
# -------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, '..', 'backend', 'data', 'raw')

def to_datetime(s):
    s_str = s.astype(str).str.replace(".0", "", regex=False).str.strip()
    return pd.to_datetime(s_str, format="%Y%m%d", errors="coerce").fillna(pd.to_datetime(s_str, errors="coerce"))

print("🧪 980 Unleashed Experiment - Loading data...")
train_members = pd.read_csv(os.path.join(DATA_PATH, 'train_members_v2.csv'))
transactions = pd.read_csv(os.path.join(DATA_PATH, 'transactions_v2.csv'))
user_logs = pd.read_csv(os.path.join(DATA_PATH, 'user_logs_aug_v2.csv'))

# -------------------------------------------------
# 2. Simple Feature Engineering (as per 980 logic)
# -------------------------------------------------
print("🧪 Processing features...")
transactions['transaction_date'] = to_datetime(transactions['transaction_date'])
tx_agg = transactions.groupby('msno').agg({
    'payment_plan_days': 'mean',
    'plan_list_price': 'mean',
    'actual_amount_paid': 'mean',
    'is_auto_renew': 'last',
    'is_cancel': 'last',
    'transaction_date': 'count'
}).reset_index()
tx_agg.columns = ['msno', 'plan_days_mean', 'plan_price_mean', 'paid_mean', 'last_auto_renew', 'last_cancel', 'tx_count']

log_feat = user_logs.copy()
log_feat['play_total'] = log_feat[['num_25', 'num_50', 'num_75', 'num_985', 'num_100']].sum(axis=1)
log_feat['completion_ratio'] = log_feat['num_100'] / (log_feat['play_total'] + 1e-9)

df = train_members.merge(tx_agg, on='msno', how='left')
df = df.merge(log_feat, on='msno', how='left')
df = df.fillna(0)

features = ['bd', 'plan_days_mean', 'plan_price_mean', 'paid_mean', 'last_auto_renew', 'last_cancel', 'tx_count', 'play_total', 'completion_ratio']
X = df[features]
y = df['is_churn']

X_train, X_valid, y_train, y_valid = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

# -------------------------------------------------
# 3. Aggressive Training (Overfitting ignored)
# -------------------------------------------------
print("🚀 Training with AGGRESSIVE hyperparameters (Depth=10, Estimators=500)...")
model = XGBClassifier(
    n_estimators=500,
    max_depth=10,
    learning_rate=0.05,
    subsample=1.0,
    colsample_bytree=1.0,
    eval_metric='auc',
    random_state=42,
    tree_method='hist'
)

model.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], verbose=100)

# -------------------------------------------------
# 4. Results
# -------------------------------------------------
train_auc = roc_auc_score(y_train, model.predict_proba(X_train)[:, 1])
valid_auc = roc_auc_score(y_valid, model.predict_proba(X_valid)[:, 1])

print("\n" + "="*50)
print("🧪 980 UNLEASHED EXPERIMENT RESULTS")
print("="*50)
print(f"Training AUC:   {train_auc:.4f}")
print(f"Validation AUC: {valid_auc:.4f}")
print(f"AUC Gap:        {train_auc - valid_auc:.4f}")
print("="*50 + "\n")
