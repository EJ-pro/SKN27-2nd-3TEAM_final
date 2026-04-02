import warnings
warnings.filterwarnings("ignore")

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tqdm.auto import tqdm
import time

from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix, f1_score
from catboost import CatBoostClassifier
import shap

# =========================================================
# 0. 경로 및 환경 설정
# =========================================================
BASE_PATH = os.path.join(os.path.dirname(__file__), '..', 'backend', 'app', 'data', 'raw')

# 데이터 로드 (상대 경로)
try:
    transactions_df = pd.read_csv(os.path.join(BASE_PATH, 'transactions_v2.csv'))
    user_logs_df = pd.read_csv(os.path.join(BASE_PATH, 'user_logs_aug_v2.csv'))
    print(f"✅ 데이터 로드 완료 (경로: {BASE_PATH})")
except Exception as e:
    print(f"❌ 데이터 로드 실패: {e}")

LABEL_DAYS = 30
RANDOM_STATE = 42
OUTPUT_DIR = "winback_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================================================
# 1. 기본 전처리
# =========================================================
def preprocess_raw_data(transactions: pd.DataFrame, user_logs: pd.DataFrame):
    tx = transactions.copy()
    logs = user_logs.copy()

    tx["transaction_date"] = pd.to_datetime(tx["transaction_date"], errors="coerce")
    tx["membership_expire_date"] = pd.to_datetime(tx["membership_expire_date"], errors="coerce")

    tx = tx.sort_values(["msno", "transaction_date"]).reset_index(drop=True)
    logs = logs.sort_values(["msno"]).reset_index(drop=True)

    tx_num_cols = ["payment_method_id", "payment_plan_days", "plan_list_price", "actual_amount_paid", "is_auto_renew", "is_cancel"]
    for col in tx_num_cols:
        tx[col] = pd.to_numeric(tx[col], errors="coerce").fillna(0)

    log_num_cols = ["num_25", "num_50", "num_75", "num_985", "num_100", "num_unq", "total_secs"]
    for col in log_num_cols:
        logs[col] = pd.to_numeric(logs[col], errors="coerce").fillna(0)

    logs["total_plays"] = logs["num_25"] + logs["num_50"] + logs["num_75"] + logs["num_985"] + logs["num_100"]
    return tx, logs

# =========================================================
# 2. 해지 이벤트 추출 / 라벨 생성
# =========================================================
def extract_cancel_events(tx: pd.DataFrame) -> pd.DataFrame:
    cancel_df = tx[tx["is_cancel"] == 1].copy()
    cancel_df = cancel_df.rename(columns={"transaction_date": "cancel_date"})
    cancel_df = cancel_df.sort_values(["msno", "cancel_date"]).reset_index(drop=True)
    cancel_df = cancel_df.drop_duplicates(subset=["msno", "cancel_date"])
    return cancel_df

def make_return_label(cancel_df: pd.DataFrame, tx: pd.DataFrame, label_days: int = 30) -> pd.DataFrame:
    tx_sorted = tx.sort_values(["msno", "transaction_date"]).copy()
    tx_grouped = {msno: g.reset_index(drop=True) for msno, g in tx_sorted.groupby("msno", sort=False)}
    result_rows = []
    for _, row in tqdm(cancel_df.iterrows(), total=len(cancel_df), desc="라벨 생성"):
        msno, cancel_date = row["msno"], row["cancel_date"]
        tx_user = tx_grouped.get(msno)
        returned, first_return_date = 0, pd.NaT
        if tx_user is not None and not tx_user.empty:
            future_tx = tx_user[(tx_user["transaction_date"] > cancel_date) & (tx_user["transaction_date"] <= cancel_date + pd.Timedelta(days=label_days))]
            if not future_tx.empty:
                paid_tx = future_tx[(future_tx["actual_amount_paid"] > 0) | (future_tx["payment_plan_days"] > 0)]
                if not paid_tx.empty:
                    returned, first_return_date = 1, paid_tx["transaction_date"].iloc[0]
        out = row.to_dict()
        out.update({"return_30d": returned, "first_return_date": first_return_date})
        result_rows.append(out)
    return pd.DataFrame(result_rows)

# =========================================================
# 3. 거래 기반 feature
# =========================================================
def build_transaction_features(cancel_base_df: pd.DataFrame, tx: pd.DataFrame) -> pd.DataFrame:
    tx_sorted = tx.sort_values(["msno", "transaction_date"]).copy()
    tx_grouped = {msno: g.reset_index(drop=True) for msno, g in tx_sorted.groupby("msno", sort=False)}
    feature_rows = []
    for _, row in tqdm(cancel_base_df.iterrows(), total=len(cancel_base_df), desc="거래 feature 생성"):
        msno, cancel_date = row["msno"], row["cancel_date"]
        tx_user = tx_grouped.get(msno)
        if tx_user is None or tx_user.empty:
            feature_rows.append({"msno": msno, "cancel_date": cancel_date, "tx_count_before_cancel": 0, "avg_actual_amount_paid": 0, "last_actual_amount_paid": 0, "avg_plan_days": 0, "last_plan_days": 0, "avg_plan_list_price": 0, "last_plan_list_price": 0, "last_is_auto_renew": 0, "last_payment_method_id": -1, "tenure_days_before_cancel": 0, "days_since_last_transaction": 9999, "tx_count_last_30d": 0, "tx_count_last_90d": 0, "paid_sum_last_30d": 0, "paid_sum_last_90d": 0})
            continue
        hist = tx_user[tx_user["transaction_date"] < cancel_date]
        if hist.empty:
            feature_rows.append({"msno": msno, "cancel_date": cancel_date, "tx_count_before_cancel": 0, "avg_actual_amount_paid": 0, "last_actual_amount_paid": 0, "avg_plan_days": 0, "last_plan_days": 0, "avg_plan_list_price": 0, "last_plan_list_price": 0, "last_is_auto_renew": 0, "last_payment_method_id": -1, "tenure_days_before_cancel": 0, "days_since_last_transaction": 9999, "tx_count_last_30d": 0, "tx_count_last_90d": 0, "paid_sum_last_30d": 0, "paid_sum_last_90d": 0})
            continue
        hist_30, hist_90 = hist[hist["transaction_date"] >= cancel_date - pd.Timedelta(days=30)], hist[hist["transaction_date"] >= cancel_date - pd.Timedelta(days=90)]
        feature_rows.append({"msno": msno, "cancel_date": cancel_date, "tx_count_before_cancel": len(hist), "avg_actual_amount_paid": hist["actual_amount_paid"].mean(), "last_actual_amount_paid": hist["actual_amount_paid"].iloc[-1], "avg_plan_days": hist["payment_plan_days"].mean(), "last_plan_days": hist["payment_plan_days"].iloc[-1], "avg_plan_list_price": hist["plan_list_price"].mean(), "last_plan_list_price": hist["plan_list_price"].iloc[-1], "last_is_auto_renew": hist["is_auto_renew"].iloc[-1], "last_payment_method_id": hist["payment_method_id"].iloc[-1], "tenure_days_before_cancel": (cancel_date - hist["transaction_date"].iloc[0]).days, "days_since_last_transaction": (cancel_date - hist["transaction_date"].iloc[-1]).days, "tx_count_last_30d": len(hist_30), "tx_count_last_90d": len(hist_90), "paid_sum_last_30d": hist_30["actual_amount_paid"].sum(), "paid_sum_last_90d": hist_90["actual_amount_paid"].sum()})
    return pd.DataFrame(feature_rows)

# =========================================================
# 4. Baseline 로그 feature
# =========================================================
def build_log_features_baseline(logs: pd.DataFrame) -> pd.DataFrame:
    log_feat = logs.copy()
    log_feat["avg_secs_per_unq"] = np.where(log_feat["num_unq"] > 0, log_feat["total_secs"] / log_feat["num_unq"], 0)
    log_feat["completion_heavy_ratio"] = np.where(log_feat["total_plays"] > 0, log_feat["num_100"] / log_feat["total_plays"], 0)
    log_feat["short_play_ratio"] = np.where(log_feat["total_plays"] > 0, log_feat["num_25"] / log_feat["total_plays"], 0)
    return log_feat[["msno", "num_25", "num_50", "num_75", "num_985", "num_100", "num_unq", "total_secs", "total_plays", "avg_secs_per_unq", "completion_heavy_ratio", "short_play_ratio"]].copy()

# =========================================================
# 5. Reconstruction용 daily logs 생성
# =========================================================
def merge_intervals(intervals):
    if not intervals: return []
    intervals = sorted(intervals, key=lambda x: x[0])
    merged = [intervals[0]]
    for cur_s, cur_e in intervals[1:]:
        last_s, last_e = merged[-1]
        if cur_s <= last_e + pd.Timedelta(days=1): merged[-1] = (last_s, max(last_e, cur_e))
        else: merged.append((cur_s, cur_e))
    return merged

def build_user_active_intervals(tx_user: pd.DataFrame):
    intervals = []
    for _, row in tx_user.iterrows():
        s, e = row["transaction_date"], row["membership_expire_date"]
        if pd.isna(s) or pd.isna(e) or e < s: continue
        intervals.append((s.normalize(), e.normalize()))
    return merge_intervals(intervals)

def reconstruct_daily_logs_from_active_periods(tx: pd.DataFrame, logs: pd.DataFrame, weighting: str = "uniform"):
    logs_idx = logs.set_index("msno")
    tx_grouped = {msno: g.reset_index(drop=True) for msno, g in tx.groupby("msno", sort=False)}
    frames = []
    for msno in tqdm(tx["msno"].dropna().unique(), desc="daily logs 재구성"):
        if msno not in logs_idx.index: continue
        tx_user = tx_grouped.get(msno)
        if tx_user is None or tx_user.empty: continue
        intervals = build_user_active_intervals(tx_user)
        if not intervals: continue
        agg = logs_idx.loc[msno]
        if isinstance(agg, pd.DataFrame): agg = agg.iloc[0]
        date_arrays = [pd.date_range(s, e, freq="D") for s, e in intervals]
        all_days = pd.DatetimeIndex(np.concatenate([arr.values for arr in date_arrays]))
        n = len(all_days)
        if n == 0: continue
        weights = np.ones(n) / n if weighting == "uniform" else np.linspace(1.0, 2.0, n) / np.linspace(1.0, 2.0, n).sum()
        frames.append(pd.DataFrame({"msno": msno, "log_date": all_days, "num_25": agg["num_25"]*weights, "num_50": agg["num_50"]*weights, "num_75": agg["num_75"]*weights, "num_985": agg["num_985"]*weights, "num_100": agg["num_100"]*weights, "num_unq": agg["num_unq"]*weights, "total_secs": agg["total_secs"]*weights, "total_plays": agg["total_plays"]*weights}))
    if not frames: return pd.DataFrame(columns=["msno", "log_date", "num_25", "num_50", "num_75", "num_985", "num_100", "num_unq", "total_secs", "total_plays"])
    daily_logs = pd.concat(frames, ignore_index=True)
    daily_logs["log_date"] = pd.to_datetime(daily_logs["log_date"])
    return daily_logs.sort_values(["msno", "log_date"]).reset_index(drop=True)

# =========================================================
# 6. Reconstruction 로그 feature
# =========================================================
def build_log_features_reconstructed(cancel_base_df: pd.DataFrame, daily_logs: pd.DataFrame) -> pd.DataFrame:
    if daily_logs.empty: return pd.DataFrame(columns=["msno", "cancel_date", "log_count_last_7d", "log_count_last_30d", "log_count_last_90d", "plays_last_7d", "plays_last_30d", "plays_last_90d", "secs_last_7d", "secs_last_30d", "secs_last_90d", "unq_last_30d", "unq_last_90d", "days_since_last_activity", "usage_drop_ratio_30d", "recent_activity_ratio_7_to_30"])
    logs_grouped = {msno: g.reset_index(drop=True) for msno, g in daily_logs.groupby("msno", sort=False)}
    feature_rows = []
    for _, row in tqdm(cancel_base_df.iterrows(), total=len(cancel_base_df), desc="recon feature 생성"):
        msno, cancel_date = row["msno"], row["cancel_date"]
        hist = logs_grouped.get(msno)
        if hist is None or hist.empty:
            feature_rows.append({"msno": msno, "cancel_date": cancel_date, "log_count_last_7d": 0, "log_count_last_30d": 0, "log_count_last_90d": 0, "plays_last_7d": 0, "plays_last_30d": 0, "plays_last_90d": 0, "secs_last_7d": 0, "secs_last_30d": 0, "secs_last_90d": 0, "unq_last_30d": 0, "unq_last_90d": 0, "days_since_last_activity": 9999, "usage_drop_ratio_30d": 0, "recent_activity_ratio_7_to_30": 0})
            continue
        hist = hist[hist["log_date"] < cancel_date]
        if hist.empty:
            feature_rows.append({"msno": msno, "cancel_date": cancel_date, "log_count_last_7d": 0, "log_count_last_30d": 0, "log_count_last_90d": 0, "plays_last_7d": 0, "plays_last_30d": 0, "plays_last_90d": 0, "secs_last_7d": 0, "secs_last_30d": 0, "secs_last_90d": 0, "unq_last_30d": 0, "unq_last_90d": 0, "days_since_last_activity": 9999, "usage_drop_ratio_30d": 0, "recent_activity_ratio_7_to_30": 0})
            continue
        last_7, last_30, last_90 = hist[hist["log_date"] >= cancel_date - pd.Timedelta(days=7)], hist[hist["log_date"] >= cancel_date - pd.Timedelta(days=30)], hist[hist["log_date"] >= cancel_date - pd.Timedelta(days=90)]
        prev_30 = hist[(hist["log_date"] >= cancel_date - pd.Timedelta(days=60)) & (hist["log_date"] < cancel_date - pd.Timedelta(days=30))]
        secs_30, p_secs_30 = last_30["total_secs"].sum(), prev_30["total_secs"].sum()
        feature_rows.append({"msno": msno, "cancel_date": cancel_date, "log_count_last_7d": len(last_7), "log_count_last_30d": len(last_30), "log_count_last_90d": len(last_90), "plays_last_7d": last_7["total_plays"].sum(), "plays_last_30d": last_30["total_plays"].sum(), "plays_last_90d": last_90["total_plays"].sum(), "secs_last_7d": last_7["total_secs"].sum(), "secs_last_30d": secs_30, "secs_last_90d": last_90["total_secs"].sum(), "unq_last_30d": last_30["num_unq"].sum(), "unq_last_90d": last_90["num_unq"].sum(), "days_since_last_activity": (cancel_date - hist["log_date"].iloc[-1]).days, "usage_drop_ratio_30d": secs_30/p_secs_30 if p_secs_30>0 else 0, "recent_activity_ratio_7_to_30": last_7["total_secs"].sum()/secs_30 if secs_30>0 else 0})
    return pd.DataFrame(feature_rows)

def add_interaction_features(df: pd.DataFrame) -> pd.DataFrame:
    eps = 1
    if {"paid_sum_last_30d", "total_plays"}.issubset(df.columns): df["paid_per_play_30d"] = df["paid_sum_last_30d"] / (df["total_plays"] + eps)
    if {"tx_count_before_cancel", "tenure_days_before_cancel"}.issubset(df.columns): df["tx_per_tenure_day"] = df["tx_count_before_cancel"] / (df["tenure_days_before_cancel"] + eps)
    if {"total_secs", "num_unq"}.issubset(df.columns): df["secs_per_unq_v2"] = df["total_secs"] / (df["num_unq"] + eps)
    if {"num_100", "num_25"}.issubset(df.columns): df["completion_vs_skip"] = (df["num_100"] + eps) / (df["num_25"] + eps)
    if {"tenure_days_before_cancel", "days_since_last_transaction"}.issubset(df.columns): df["inactive_tenure_ratio"] = df["days_since_last_transaction"] / (df["tenure_days_before_cancel"] + eps)
    if {"days_since_last_transaction", "tx_count_before_cancel"}.issubset(df.columns): df["inactive_per_tx"] = df["days_since_last_transaction"] / (df["tx_count_before_cancel"] + eps)
    return df

# =========================================================
# 7. 데이터셋 빌더 & 학습 유틸
# =========================================================
def build_winback_dataset_baseline(transactions: pd.DataFrame, user_logs: pd.DataFrame, label_days: int = 30):
    tx, logs = preprocess_raw_data(transactions, user_logs)
    labeled_df = make_return_label(extract_cancel_events(tx), tx, label_days)
    dataset = labeled_df.merge(build_transaction_features(labeled_df, tx), on=["msno", "cancel_date"], how="left").merge(build_log_features_baseline(logs), on="msno", how="left")
    return add_interaction_features(dataset.fillna(0))

def build_winback_dataset_reconstructed(transactions: pd.DataFrame, user_logs: pd.DataFrame, label_days: int = 30):
    tx, logs = preprocess_raw_data(transactions, user_logs)
    labeled_df = make_return_label(extract_cancel_events(tx), tx, label_days)
    daily_logs = reconstruct_daily_logs_from_active_periods(tx, logs)
    dataset = labeled_df.merge(build_transaction_features(labeled_df, tx), on=["msno", "cancel_date"], how="left").merge(build_log_features_reconstructed(labeled_df, daily_logs), on=["msno", "cancel_date"], how="left")
    return add_interaction_features(dataset.fillna(0)), daily_logs

def prepare_train_data(df: pd.DataFrame):
    drop_cols = ["msno", "cancel_date", "first_return_date", "return_30d", "transaction_date", "membership_expire_date"]
    feat_cols = [c for c in df.columns if c not in drop_cols and df[c].dtype.kind in "biufc"]
    return df[feat_cols], df["return_30d"], feat_cols

def train_winback_catboost(X, y, model_name="model"):
    X_train, X_valid, y_train, y_valid = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    model = CatBoostClassifier(iterations=500, depth=6, learning_rate=0.05, loss_function="Logloss", eval_metric="AUC", random_seed=42, verbose=0)
    model.fit(X_train, y_train, eval_set=(X_valid, y_valid), use_best_model=True)
    best_t, best_f1 = 0.5, 0
    proba = model.predict_proba(X_valid)[:, 1]
    for t in [i/100 for i in range(30, 71, 5)]:
        f1 = f1_score(y_valid, (proba >= t).astype(int))
        if f1 > best_f1: best_f1, best_t = f1, t
    auc = roc_auc_score(y_valid, proba)
    print(f"[{model_name}] AUC: {auc:.4f}, Best F1: {best_f1:.4f} (at {best_t})")
    result_df = X_valid.copy(); result_df.update({"y_true": y_valid.values, "pred_proba": proba})
    return model, X_train, X_valid, y_train, y_valid, result_df, {"model_name": model_name, "auc": auc}

def train_with_selected_features(df, selected_features, model_name="SelectedModel"):
    X, y, _ = prepare_train_data(df)
    X_sel = X[[f for f in selected_features if f in X.columns]]
    return train_winback_catboost(X_sel, y, model_name)

def compare_baseline_vs_reconstruction(transactions_df, user_logs_df):
    total_start = time.time()
    b_df = build_winback_dataset_baseline(transactions_df, user_logs_df)
    Xb, yb, _ = prepare_train_data(b_df)
    b_model, _, Xbv, _, ybv, _, b_metrics = train_winback_catboost(Xb, yb, "Baseline")
    r_df, daily = build_winback_dataset_reconstructed(transactions_df, user_logs_df)
    Xr, yr, _ = prepare_train_data(r_df)
    r_model, _, Xrv, _, yrv, _, r_metrics = train_winback_catboost(Xr, yr, "Reconstruction")
    print("\n[비교 결과]", pd.DataFrame([b_metrics, r_metrics]))
    print(f"🎉 전체 완료! (총 {time.time()-total_start:.2f}초)")
    return {"baseline_df": b_df, "baseline_model": b_model, "recon_df": r_df}

# =========================================================
# Main: 전수 스코어링 및 결과 저장
# =========================================================
if __name__ == "__main__":
    base_selected_features = ["tenure_days_before_cancel", "last_payment_method_id", "tx_count_before_cancel", "payment_method_id", "num_985", "inactive_tenure_ratio", "inactive_per_tx", "days_since_last_transaction", "plays_per_unq", "num_75", "num_25", "total_secs", "num_100", "num_50", "paid_per_play_30d", "total_plays", "num_unq", "tx_per_tenure_day", "secs_per_unq_v2", "completion_heavy_ratio", "completion_vs_skip"]
    
    results = compare_baseline_vs_reconstruction(transactions_df, user_logs_df)
    final_model, _, _, _, _, _, _ = train_with_selected_features(results["baseline_df"], base_selected_features, "FinalModel")
    
    df_all = results["baseline_df"].copy()
    X_all = df_all[[f for f in base_selected_features if f in df_all.columns]]
    proba_all = final_model.predict_proba(X_all)[:, 1]
    
    df_result = pd.DataFrame({"msno": df_all["msno"], "churn_proba": proba_all})
    df_result["risk_score"] = (df_result["churn_proba"] * 100).round(2)
    df_result["risk_grade"] = df_result["risk_score"].apply(lambda x: "HIGH" if x>=60 else ("MID" if x>=30 else "LOW"))
    df_result = df_result.sort_values("risk_score", ascending=False)
    
    save_path = os.path.join(os.path.dirname(__file__), "churn_risk_result.csv")
    df_result.to_csv(save_path, index=False, encoding='utf-8-sig')
    print(f"✨ 분석 완료! 결과가 {save_path} 에 저장되었습니다.")