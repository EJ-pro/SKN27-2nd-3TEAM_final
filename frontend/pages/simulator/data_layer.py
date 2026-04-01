import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st

from pages.action_board.config import HIGH_RISK_THRESHOLD, TWD_TO_KRW, EXPIRY_WINDOW_DAYS
from pages.action_board.data_layer import get_shifted_raw_data, inject_churn_probability
from pages.simulator.config import A_BASE_RETENTION, A_RETENTION_FACTOR, B_FIXED_RETENTION


@st.cache_data
def get_real_sim_data(virtual_today):
    """
    실제 DB 데이터를 로드하여 분석 기준일 기준의 고위험군 유저 풀을 생성합니다.
    """
    raw_result = get_shifted_raw_data()
    if not raw_result or "transactions" not in raw_result:
        return pd.DataFrame()

    trans_df = raw_result["transactions"].copy()
    if trans_df.empty:
        return pd.DataFrame()

    prob_df = inject_churn_probability(trans_df).copy()
    if prob_df.empty:
        return pd.DataFrame()

    # 날짜형 강제 변환
    prob_df["membership_expire_date"] = pd.to_datetime(
        prob_df["membership_expire_date"], errors="coerce"
    )

    # 이상 날짜 제거
    prob_df = prob_df.dropna(subset=["membership_expire_date"])
    prob_df = prob_df[prob_df["membership_expire_date"] >= pd.Timestamp("2000-01-01")]

    if prob_df.empty:
        return pd.DataFrame()

    # 기준일 Timestamp 통일
    virtual_today = pd.Timestamp(virtual_today).normalize()

    # 실제 존재하는 만료일 목록
    valid_dates = pd.Series(
        prob_df["membership_expire_date"].dt.normalize().unique()
    ).sort_values()

    if valid_dates.empty:
        return pd.DataFrame()

    # 사용자가 고른 날짜 이후의 가장 가까운 실제 만료일로 자동 보정
    future_dates = valid_dates[valid_dates >= virtual_today]
    if len(future_dates) > 0:
        adjusted_today = future_dates.iloc[0]
    else:
        adjusted_today = valid_dates.iloc[-1]

    # 날짜 윈도우
    window_end = adjusted_today + pd.Timedelta(days=EXPIRY_WINDOW_DAYS)

    # 분석 기준일로부터 만료 임박한 유저 필터링
    expire_dates = prob_df["membership_expire_date"].dt.normalize()
    mask_date = (
        (expire_dates >= adjusted_today) &
        (expire_dates <= window_end)
    )

    # churn_prob 컬럼 확인
    if "churn_prob" not in prob_df.columns:
        return pd.DataFrame()

    # 이탈 확률 기준 완화
    candidates = prob_df[mask_date & (prob_df["churn_prob"] >= 0.5)].copy()

    if candidates.empty:
        return pd.DataFrame()

    # 필드 정리 및 중복 컬럼 제거 (ValueError 방지)
    candidates = candidates.rename(
        columns={
            "msno": "user_id",
            "churn_prob": "churn_probability"
        }
    )
    candidates = candidates.loc[:, ~candidates.columns.duplicated()]

    # 가입 기간 (임시 시뮬레이션용)
    rng = np.random.default_rng(42)
    candidates["membership_duration_months"] = rng.integers(1, 13, len(candidates))

    return candidates


def get_simulator_default_date():
    """
    데이터 시점에 맞는 기본 분석 기준일을 자동 계산합니다.
    membership_expire_date의 최댓값 근처를 기본값으로 사용합니다.
    """
    raw_result = get_shifted_raw_data()
    if not raw_result or "transactions" not in raw_result:
        return datetime.today().date()

    trans_df = raw_result["transactions"].copy()
    if trans_df.empty or "membership_expire_date" not in trans_df.columns:
        return datetime.today().date()

    trans_df["membership_expire_date"] = pd.to_datetime(
        trans_df["membership_expire_date"], errors="coerce"
    )
    trans_df = trans_df.dropna(subset=["membership_expire_date"])

    if trans_df.empty:
        return datetime.today().date()

    max_expiry = trans_df["membership_expire_date"].max()

    # 마지막 만료일 기준으로 7일 전을 기본 날짜로 사용
    default_date = (max_expiry - pd.Timedelta(days=7)).date()
    return default_date


def calculate_retention_rates(discount_rate):
    """
    할인율에 따른 예상 방어율을 계산합니다.
    """
    retention_a = (A_BASE_RETENTION + (discount_rate * A_RETENTION_FACTOR)) / 100
    retention_b = B_FIXED_RETENTION / 100
    return retention_a, retention_b


def calculate_roi_data(target_a_count, target_b_count, retention_a, retention_b, discount_rate, avg_price):
    """
    3개월간의 예상 ROI 데이터를 생성합니다.
    """
    rev_a = [
        (target_a_count * retention_a) * (avg_price * (1 - discount_rate / 100)) * TWD_TO_KRW,
        (target_a_count * retention_a) * avg_price * TWD_TO_KRW,
        (target_a_count * retention_a) * avg_price * TWD_TO_KRW
    ]

    rev_b = [
        (target_b_count * retention_b) * 0,
        (target_b_count * retention_b) * avg_price * TWD_TO_KRW,
        (target_b_count * retention_b) * avg_price * TWD_TO_KRW
    ]

    roi_df = pd.DataFrame({
        "경과 월": ["1개월 후", "2개월 후", "3개월 후"] * 2,
        "그룹": ["할인 쿠폰군 (A)"] * 3 + ["무료 연장군 (B)"] * 3,
        "예상 매출액": rev_a + rev_b
    })

    return roi_df, sum(rev_a), sum(rev_b)