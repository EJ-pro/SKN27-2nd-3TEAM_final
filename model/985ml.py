import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import glob
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

# -------------------------------------------------
# 1. Path Configuration
# -------------------------------------------------
def find_data_file(pattern):
    # Try multiple ways to find the file
    paths = [
        os.path.join('backend', 'data', 'raw', pattern),
        os.path.join('..', 'backend', 'data', 'raw', pattern),
        pattern
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    # Try glob
    matches = glob.glob(f"**/{pattern}", recursive=True)
    if matches:
        return matches[0]
    return None

# -------------------------------------------------
# 2. Data Loading
# -------------------------------------------------
print("📦 Loading data for 985 model (conversion attempt)...")
try:
    train_path = find_data_file('train_members_v2.csv')
    tx_path = find_data_file('transactions_v2.csv')
    # If raw logs fail, fallback to augmented
    log_path = find_data_file('user_logs_v2.csv')
    if not log_path:
        log_path = find_data_file('user_logs_aug_v2.csv')
        print("⚠️  Warning: Using augmented logs instead of raw daily logs.")

    if not all([train_path, tx_path, log_path]):
        raise FileNotFoundError(f"Missing one or more required files. Found: {train_path}, {tx_path}, {log_path}")

    print(f"Loading {train_path}...")
    train_members = pd.read_csv(train_path)
    print(f"Loading {tx_path}...")
    transactions = pd.read_csv(tx_path)
    print(f"Loading {log_path}...")
    user_logs = pd.read_csv(log_path, nrows=500000)
    print("✅ Data loading complete.")
except Exception as e:
    print(f"❌ Error loading data: {e}")
    exit(1)

# -------------------------------------------------
# 3. Simple Feature Engineering
# -------------------------------------------------
def to_datetime(s):
    s_str = s.astype(str).str.replace(".0", "", regex=False).str.strip()
    return pd.to_datetime(s_str, format="%Y%m%d", errors="coerce").fillna(pd.to_datetime(s_str, errors="coerce"))

train_members['snapshot_date'] = pd.to_datetime('2017-03-31')

# Aggregations
transactions['transaction_date'] = to_datetime(transactions['transaction_date'])
tx_agg = transactions.groupby('msno').agg(
    tx_count=('msno', 'count'),
    last_auto_renew=('is_auto_renew', 'last')
).reset_index()

# Log features
if 'date' in user_logs.columns:
    user_logs['date'] = to_datetime(user_logs['date'])
    log_agg = user_logs.groupby('msno').agg(
        active_days=('date', 'count'),
        total_secs=('total_secs', 'sum')
    ).reset_index()
else:
    # Handle pre-aggregated logs (like user_logs_aug_v2.csv)
    log_agg = user_logs.copy()
    if 'msno' not in log_agg.columns: log_agg['msno'] = log_agg.index # if index based

# -------------------------------------------------
# 4. Merge & Modeling
# -------------------------------------------------
df = train_members.merge(tx_agg, on='msno', how='left')
df = df.merge(log_agg, on='msno', how='left')
df = df.fillna(0)
df['gender_val'] = df['gender'].map({'female': 1, 'male': 2}).fillna(0)

features = ['city', 'bd', 'registered_via', 'tx_count', 'last_auto_renew', 'gender_val']
# Add log features if they exist
for f in ['active_days', 'total_secs', 'play_total', 'completion_ratio']:
    if f in df.columns: features.append(f)

X = df[features]
y = df['is_churn']

X_train, X_valid, y_train, y_valid = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

print(f"🚀 Training XGBoost model for Diagnostic...")
model = XGBClassifier(n_estimators=50, max_depth=5, random_state=42)
model.fit(X_train, y_train)

# Metrics
train_auc = roc_auc_score(y_train, model.predict_proba(X_train)[:, 1])
valid_auc = roc_auc_score(y_valid, model.predict_proba(X_valid)[:, 1])

print("\n" + "="*50)
print("🔍 OVERFITTING DIAGNOSTIC REPORT (985)")
print("="*50)
print(f"Training AUC:   {train_auc:.4f}")
print(f"Validation AUC: {valid_auc:.4f}")
print(f"AUC Gap:        {train_auc - valid_auc:.4f}")
print("="*50 + "\n")

# Save predictions
print("💾 Saving 985model.csv...")
full_probs = model.predict_proba(X)[:, 1]
output = pd.DataFrame({'msno': df['msno'], 'churn_probability': full_probs})
output.to_csv('985model.csv', index=False)
print("Done!")
