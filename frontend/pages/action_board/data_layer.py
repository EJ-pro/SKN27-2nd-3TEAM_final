"""
data_layer.py — 데이터 로딩 및 전처리 전담 모듈.

책임:
  - CSV 파일 읽기 및 날짜 타입 변환
  - 시간 시프트(Time Shifting) 적용
  - 파일 부재 시 UI 테스트용 더미 데이터 생성
  - 이탈 확률 컬럼 주입 (모델 미연동 시 더미, 연동 시 실제 추론)

이 모듈은 UI 로직을 알지 못합니다. streamlit을 import하지 않습니다.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from pages.action_board.config import DATA_DIR, FILES, TIME_OFFSET_DAYS, SCALE_FACTOR


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _shift_date_columns(df: pd.DataFrame, offset: timedelta) -> pd.DataFrame:
    """날짜 관련 컬럼을 일괄적으로 offset만큼 시프트합니다."""
    # 공백 제거 (KeyError 방지)
    df.columns = df.columns.str.strip()
    date_cols = [c for c in df.columns if "date" in c or "time" in c]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], format="%Y%m%d", errors="coerce").fillna(
            pd.to_datetime(df[col], errors="coerce")
        ) + offset
    return df


def _make_dummy_members(today: datetime, n: int = 100) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "msno": [f"user_{i}" for i in range(n)],
        "registration_init_time": [
            today - timedelta(days=int(d))
            for d in rng.integers(30, 1000, n)
        ],
    })


def _make_dummy_transactions(today: datetime, n: int = 100) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "msno":                  [f"user_{i}" for i in range(n)],
        "membership_expire_date": [today + timedelta(days=int(d)) for d in rng.integers(-5, 10, n)],
        "plan_list_price":        [149] * n,
        "is_auto_renew":          rng.choice([0, 1], n, p=[0.3, 0.7]),
        "transaction_date":       [today - timedelta(days=int(d)) for d in rng.integers(1, 30, n)],
    })


def _make_dummy_user_logs(today: datetime, n: int = 100) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "msno":   [f"user_{i}" for i in range(n)],
        "num_25": rng.integers(0, 50, n),
        "date":   [today - timedelta(days=1)] * n,
    })


# ── 공개 인터페이스 ───────────────────────────────────────────────────────────

def load_raw_data() -> dict[str, pd.DataFrame]:
    """
    CSV 파일을 읽고 날짜를 시프트하여 반환합니다.
    파일이 없으면 더미 데이터로 대체하며, 콘솔에 경고를 출력합니다.
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    offset = timedelta(days=TIME_OFFSET_DAYS)
    dummy_factories = {
        "members":      _make_dummy_members,
        "transactions": _make_dummy_transactions,
        "user_logs":    _make_dummy_user_logs,
    }
    result: dict[str, pd.DataFrame] = {}

    for key, fname in FILES.items():
        path = f"{DATA_DIR}{fname}"
        try:
            df = pd.read_csv(path)
            df = _shift_date_columns(df, offset)
            result[key] = df
        except FileNotFoundError:
            print(f"[WARN] {path} 없음 → 더미 데이터로 대체")
            result[key] = dummy_factories[key](today)


    # [Ground Truth 연동] members의 is_churn 정보를 transactions에 병합
    if "transactions" in result and "members" in result:
        mems = result["members"]
        trans = result["transactions"]
        if "is_churn" in mems.columns:
            trans = pd.merge(trans, mems[["msno", "is_churn"]], on="msno", how="left")
            trans["is_churn"] = trans["is_churn"].fillna(0)
            result["transactions"] = trans

    # [로그 데이터 요약 연동] user_logs에서 유저 활동성 추출
    if "transactions" in result and "user_logs" in result:
        logs = result["user_logs"]
        trans = result["transactions"]
        
        # 유저별 최신 접속일 및 활동량 합계
        log_summary = logs.groupby("msno").agg({
            "date": "max",
            "num_25": "sum",
            "num_100": "sum"
        }).reset_index()
        log_summary.columns = ["msno", "last_activity_date", "total_25", "total_100"]
        
        trans = pd.merge(trans, log_summary, on="msno", how="left")
        result["transactions"] = trans

    return result


def inject_churn_probability(
    transactions: pd.DataFrame,
    model=None,
) -> pd.DataFrame:
    """
    transactions에 'churn_prob' 컬럼을 추가합니다.

    - model이 None이면 is_auto_renew 기반 더미 확률 사용 (현재 상태).
    - model이 주입되면 predict_proba로 교체하세요.

    Args:
        transactions: 원본 트랜잭션 DataFrame
        model: sklearn 호환 모델 (옵션). None이면 더미 로직 사용.

    Returns:
        'churn_prob' 컬럼이 추가된 DataFrame (원본 변경 없음).
    """
    df = transactions.copy()

    if "churn_prob" in df.columns:
        return df  # 이미 있으면 그대로

    if model is not None:
        # ── 실제 모델 연동 시 이 블록을 채우세요 ──────────────────────────
        raise NotImplementedError("모델 피처 추출 로직을 여기에 구현하세요.")

    # [Ground Truth 우선순위] is_churn 데이터가 있으면 확률을 맵핑
    if "is_churn" in df.columns:
        rng = np.random.default_rng(42)
        df["churn_prob"] = df["is_churn"].apply(
            lambda x: rng.uniform(0.85, 1.0) if x == 1 else rng.uniform(0.0, 0.4)
        )
        return df

    # 더미: 자동결제 해지 여부로 고위험/저위험 구분
    rng = np.random.default_rng(42)
    n = len(df)
    auto_renew = df["is_auto_renew"].values

    probs = np.where(
        auto_renew == 0,
        rng.uniform(0.7, 1.0, n),   # 해지 → 고위험
        rng.uniform(0.0, 0.6, n),   # 유지 → 저위험
    )
    df["churn_prob"] = probs
    return df