"""
data_layer.py
- Streamlit 프론트에서 MySQL(churn_db)에 직접 연결
- members / transactions / user_logs / churn_predictions 조회
- 화면에서 바로 쓸 수 있게 DataFrame 가공
"""

from __future__ import annotations

import os
import numpy as np
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

from pages.action_board.config import HIGH_RISK_THRESHOLD


# ── DB 연결 ───────────────────────────────────────────────────────────────
# 빠르게 진행하려고 기본값도 넣어둠
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root1234")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3307")
DB_NAME = os.getenv("DB_NAME", "churn_db")

DB_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)

engine = create_engine(
    DB_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
)


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────
def _parse_date_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df.columns = df.columns.str.strip()

    date_cols = [c for c in df.columns if ("date" in c.lower()) or ("time" in c.lower())]
    for col in date_cols:
        yyyymmdd = pd.to_datetime(df[col], format="%Y%m%d", errors="coerce")
        general = pd.to_datetime(df[col], errors="coerce")
        df[col] = yyyymmdd.fillna(general)

    return df

print("DB_URL =", DB_URL)
def _read_table(table_name: str) -> pd.DataFrame:
    with engine.connect() as conn:
        df = pd.read_sql(text(f"SELECT * FROM {table_name}"), conn)
    return _parse_date_columns(df)


# ── 공개 함수 ─────────────────────────────────────────────────────────────
@st.cache_data
def load_raw_data() -> dict[str, pd.DataFrame]:
    members = _read_table("members")
    transactions = _read_table("transactions")
    user_logs = _read_table("user_logs")

    # churn_predictions 는 있을 수도 있고 없을 수도 있게 처리
    try:
        predictions = _read_table("churn_predictions")
    except Exception:
        predictions = pd.DataFrame()

    # 1) members.is_churn 병합
    if not members.empty and not transactions.empty:
        if "msno" in members.columns and "msno" in transactions.columns:
            if "is_churn" in members.columns and "is_churn" not in transactions.columns:
                transactions = pd.merge(
                    transactions,
                    members[["msno", "is_churn"]],
                    on="msno",
                    how="left"
                )
                transactions["is_churn"] = transactions["is_churn"].fillna(0)

    # 2) user_logs 요약 병합
    # 주의: 현재 스키마엔 user_logs 날짜 컬럼이 없음
    if not user_logs.empty and not transactions.empty:
        if "msno" in user_logs.columns and "msno" in transactions.columns:
            agg_dict = {}
            for col in ["num_25", "num_50", "num_75", "num_985", "num_100", "num_unq", "total_secs"]:
                if col in user_logs.columns:
                    agg_dict[col] = "sum"

            if agg_dict:
                log_summary = user_logs.groupby("msno", as_index=False).agg(agg_dict)

                rename_map = {}
                if "num_25" in log_summary.columns:
                    rename_map["num_25"] = "total_25"
                if "num_50" in log_summary.columns:
                    rename_map["num_50"] = "total_50"
                if "num_75" in log_summary.columns:
                    rename_map["num_75"] = "total_75"
                if "num_985" in log_summary.columns:
                    rename_map["num_985"] = "total_985"
                if "num_100" in log_summary.columns:
                    rename_map["num_100"] = "total_100"
                if "num_unq" in log_summary.columns:
                    rename_map["num_unq"] = "total_unq"
                if "total_secs" in log_summary.columns:
                    rename_map["total_secs"] = "sum_total_secs"

                log_summary = log_summary.rename(columns=rename_map)

                transactions = pd.merge(
                    transactions,
                    log_summary,
                    on="msno",
                    how="left"
                )

    return {
        "members": members,
        "transactions": transactions,
        "user_logs": user_logs,
        "predictions": predictions,
    }


def inject_churn_probability(
    transactions: pd.DataFrame,
    model=None,
) -> pd.DataFrame:
    """
    우선순위
    1. churn_predictions 테이블 값 사용
    2. transactions에 이미 churn_prob 있으면 사용
    3. is_churn 기반 더미
    4. is_auto_renew 기반 더미
    """
    df = transactions.copy()
    if df.empty:
        return df

    raw = load_raw_data()
    predictions = raw.get("predictions", pd.DataFrame())

    # 1) churn_predictions 우선
    if not predictions.empty and "msno" in predictions.columns:
        pred_df = predictions.copy()

        # prediction_date가 있으면 최신 예측만 사용
        if "prediction_date" in pred_df.columns:
            pred_df = pred_df.sort_values("prediction_date").drop_duplicates("msno", keep="last")

        keep_cols = ["msno"]
        if "churn_probability" in pred_df.columns:
            keep_cols.append("churn_probability")
        if "risk_grade" in pred_df.columns:
            keep_cols.append("risk_grade")
        if "main_reason_code" in pred_df.columns:
            keep_cols.append("main_reason_code")

        pred_df = pred_df[keep_cols]

        df = pd.merge(df, pred_df, on="msno", how="left")

        if "churn_probability" in df.columns:
            df["churn_prob"] = df["churn_probability"]

        if "churn_prob" in df.columns and df["churn_prob"].notna().any():
            # 예측 없는 행만 fallback
            missing_mask = df["churn_prob"].isna()

            if missing_mask.any():
                rng = np.random.default_rng(42)
                if "is_churn" in df.columns:
                    df.loc[missing_mask, "churn_prob"] = df.loc[missing_mask, "is_churn"].apply(
                        lambda x: rng.uniform(0.85, 1.0) if x == 1 else rng.uniform(0.0, 0.4)
                    )
                elif "is_auto_renew" in df.columns:
                    df.loc[missing_mask, "churn_prob"] = np.where(
                        df.loc[missing_mask, "is_auto_renew"].fillna(1).values == 0,
                        rng.uniform(0.7, 1.0, missing_mask.sum()),
                        rng.uniform(0.0, 0.6, missing_mask.sum()),
                    )
                else:
                    df.loc[missing_mask, "churn_prob"] = rng.uniform(0.0, 1.0, missing_mask.sum())

            # risk_grade 없으면 churn_prob로 생성
            if "risk_grade" not in df.columns:
                df["risk_grade"] = df["churn_prob"].apply(
                    lambda x: "위험도 높음" if x >= HIGH_RISK_THRESHOLD else "위험도 중간"
                )

            # main_reason_code 없으면 간단 규칙으로 생성
            if "main_reason_code" not in df.columns:
                def determine_reason(row):
                    if row.get("is_cancel") == 1:
                        return "멤버십 직접해지"
                    if row.get("is_auto_renew") == 0:
                        return "자동결제 미등록"
                    return "활동성 저하(추정)"
                df["main_reason_code"] = df.apply(determine_reason, axis=1)

            return df

    # 2) 이미 churn_prob 있으면 그대로
    if "churn_prob" in df.columns:
        return df

    # 3) fallback
    rng = np.random.default_rng(42)

    if "is_churn" in df.columns:
        df["churn_prob"] = df["is_churn"].apply(
            lambda x: rng.uniform(0.85, 1.0) if x == 1 else rng.uniform(0.0, 0.4)
        )
    elif "is_auto_renew" in df.columns:
        df["churn_prob"] = np.where(
            df["is_auto_renew"].fillna(1).values == 0,
            rng.uniform(0.7, 1.0, len(df)),
            rng.uniform(0.0, 0.6, len(df)),
        )
    else:
        df["churn_prob"] = rng.uniform(0.0, 1.0, len(df))

    if "risk_grade" not in df.columns:
        df["risk_grade"] = df["churn_prob"].apply(
            lambda x: "위험도 높음" if x >= HIGH_RISK_THRESHOLD else "위험도 중간"
        )

    if "main_reason_code" not in df.columns:
        def determine_reason(row):
            if row.get("is_cancel") == 1:
                return "멤버십 직접해지"
            if row.get("is_auto_renew") == 0:
                return "자동결제 미등록"
            return "활동성 저하(추정)"
        df["main_reason_code"] = df.apply(determine_reason, axis=1)

    return df