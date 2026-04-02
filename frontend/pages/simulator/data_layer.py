import pandas as pd
import numpy as np
from datetime import datetime
import streamlit as st

from pages.action_board.config import HIGH_RISK_THRESHOLD, TWD_TO_KRW, EXPIRY_WINDOW_DAYS
from pages.action_board.data_layer import get_shifted_raw_data, inject_churn_probability
from pages.simulator.config import (
    A_PRICE_SENSITIVITY_K, A_MAX_RETENTION_CAP,
    B_BASE_RETENTION, B_LOYALTY_SCALE, B_MAX_RETENTION_CAP,
    MONTHLY_CHURN_DECAY, B_FREE_EXTENSION_MONTHS, SIMULATION_MONTHS,
)


# ══════════════════════════════════════════════════════════════
# 데이터 로드
# ══════════════════════════════════════════════════════════════

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

    prob_df["membership_expire_date"] = pd.to_datetime(
        prob_df["membership_expire_date"], errors="coerce"
    )
    prob_df = prob_df.dropna(subset=["membership_expire_date"])
    prob_df = prob_df[prob_df["membership_expire_date"] >= pd.Timestamp("2000-01-01")]

    if prob_df.empty:
        return pd.DataFrame()

    virtual_today = pd.Timestamp(virtual_today).normalize()
    valid_dates = pd.Series(
        prob_df["membership_expire_date"].dt.normalize().unique()
    ).sort_values()

    future_dates = valid_dates[valid_dates >= virtual_today]
    adjusted_today = future_dates.iloc[0] if len(future_dates) > 0 else valid_dates.iloc[-1]

    window_end  = adjusted_today + pd.Timedelta(days=EXPIRY_WINDOW_DAYS)
    expire_dates = prob_df["membership_expire_date"].dt.normalize()
    mask_date = (expire_dates >= adjusted_today) & (expire_dates <= window_end)

    if "churn_prob" not in prob_df.columns:
        return pd.DataFrame()

    candidates = prob_df[mask_date & (prob_df["churn_prob"] >= 0.5)].copy()
    if candidates.empty:
        return pd.DataFrame()

    candidates = candidates.rename(columns={
        "msno": "user_id",
        "churn_prob": "churn_probability",
    })
    candidates = candidates.loc[:, ~candidates.columns.duplicated()]

    rng = np.random.default_rng(42)
    candidates["membership_duration_months"] = rng.integers(1, 13, len(candidates))

    return candidates


def get_simulator_default_date():
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
    return (max_expiry - pd.Timedelta(days=7)).date()


# ══════════════════════════════════════════════════════════════
# Group A — 가격 탄력성 기반 방어율
# ══════════════════════════════════════════════════════════════

def calc_individual_retention_a(churn_prob: float, discount_rate_pct: float) -> float:
    """
    개인별 방어율 (가격 탄력성 모델)

    수식:
        retention = 1 - churn_prob * exp(-k * d)

    - churn_prob : 모델이 예측한 이탈 확률 (0~1)
    - d          : 할인율 (0~1)
    - k          : 가격 민감도 계수 (A_PRICE_SENSITIVITY_K)

    직관:
        할인이 없으면 (d=0) → 이탈 확률이 그대로 작동 → retention 낮음
        할인이 높을수록 → exp 항이 0에 수렴 → churn_prob 억제 → retention 높음
    """
    d = discount_rate_pct / 100.0
    raw = 1.0 - churn_prob * np.exp(-A_PRICE_SENSITIVITY_K * d)
    return float(np.clip(raw, 0.0, A_MAX_RETENTION_CAP))


def calc_group_retention_a(churn_probs: pd.Series, discount_rate_pct: float) -> float:
    """그룹 평균 방어율 (개인 방어율의 평균)"""
    individual = churn_probs.apply(
        lambda p: calc_individual_retention_a(p, discount_rate_pct)
    )
    return float(individual.mean())


# ══════════════════════════════════════════════════════════════
# Group B — 로열티 가중 방어율
# ══════════════════════════════════════════════════════════════

def calc_individual_retention_b(duration_months: float) -> float:
    """
    개인별 방어율 (가입 기간 로열티 모델)

    수식:
        retention = base * (1 + ln(1 + m) / loyalty_scale)

    - m            : 가입 기간 (개월)
    - base         : 기본 방어율 (B_BASE_RETENTION)
    - loyalty_scale: 로그 가중치 스케일 (B_LOYALTY_SCALE)

    직관:
        가입 기간이 길수록 무료 연장 제공에 더 반응 (로그 체감)
        1개월: base * 1.17,  6개월: base * 1.49,  12개월: base * 1.64
    """
    raw = B_BASE_RETENTION * (1.0 + np.log1p(duration_months) / B_LOYALTY_SCALE)
    return float(np.clip(raw, 0.0, B_MAX_RETENTION_CAP))


def calc_group_retention_b(durations: pd.Series) -> float:
    """그룹 평균 방어율"""
    individual = durations.apply(calc_individual_retention_b)
    return float(individual.mean())


# ══════════════════════════════════════════════════════════════
# 레거시 래퍼 (UI 호환)
# ══════════════════════════════════════════════════════════════

def calculate_retention_rates(discount_rate: float,
                               sim_df: pd.DataFrame | None = None,
                               target_b_df: pd.DataFrame | None = None):
    """
    UI에서 호출하는 통합 방어율 계산 함수.

    sim_df / target_b_df 가 없으면 집계 수식으로 근사값 반환 (하위 호환).
    있으면 실제 개인별 데이터 기반으로 계산.
    """
    if sim_df is not None and not sim_df.empty and "churn_probability" in sim_df.columns:
        ret_a = calc_group_retention_a(sim_df["churn_probability"], discount_rate)
    else:
        # fallback: 집계 근사
        d = discount_rate / 100.0
        avg_churn = 0.72  # 고위험군 평균 이탈 확률 추정
        ret_a = float(np.clip(1.0 - avg_churn * np.exp(-A_PRICE_SENSITIVITY_K * d), 0, A_MAX_RETENTION_CAP))

    if target_b_df is not None and not target_b_df.empty and "membership_duration_months" in target_b_df.columns:
        ret_b = calc_group_retention_b(target_b_df["membership_duration_months"])
    else:
        # fallback: 가입 기간 6개월 가정
        ret_b = calc_individual_retention_b(6)

    return ret_a, ret_b


# ══════════════════════════════════════════════════════════════
# ROI 계산 — 월별 잔존 유저 × 결제액 누적
# ══════════════════════════════════════════════════════════════

def calculate_roi_data(
    target_a_count: int,
    target_b_count: int,
    ret_a: float,
    ret_b: float,
    discount_rate: float,
    avg_price: float,
    sim_df: pd.DataFrame | None = None,
    target_b_df: pd.DataFrame | None = None,
):
    """
    SIMULATION_MONTHS 개월간 월별 예상 매출 계산.

    Group A (할인 쿠폰):
        - 방어 성공 유저 = target_a_count * ret_a
        - 1개월: 할인가 결제 (avg_price * (1 - d))
        - 2개월~: 정상가 결제, 단 매월 MONTHLY_CHURN_DECAY 비율 추가 이탈

    Group B (무료 연장):
        - 방어 성공 유저 = target_b_count * ret_b
        - 1개월 ~ B_FREE_EXTENSION_MONTHS: 매출 0 (무료 기간)
        - 이후: 정상가 결제, 동일 감가 적용
    """
    d = discount_rate / 100.0

    # 월별 잔존 유저 수 (감가 반영)
    def survivors(initial: float, month: int) -> float:
        """month=1부터 시작. 매월 MONTHLY_CHURN_DECAY 비율 추가 이탈."""
        return initial * ((1 - MONTHLY_CHURN_DECAY) ** (month - 1))

    months = list(range(1, SIMULATION_MONTHS + 1))
    labels = [f"{m}개월 후" for m in months]

    # 초기 방어 성공 유저
    init_a = target_a_count * ret_a
    init_b = target_b_count * ret_b

    rev_a, rev_b = [], []
    for m in months:
        s_a = survivors(init_a, m)
        price_a = avg_price * (1 - d) if m == 1 else avg_price
        rev_a.append(s_a * price_a * TWD_TO_KRW)

        s_b = survivors(init_b, m)
        price_b = 0.0 if m <= B_FREE_EXTENSION_MONTHS else avg_price
        rev_b.append(s_b * price_b * TWD_TO_KRW)

    roi_df = pd.DataFrame({
        "경과 월": labels * 2,
        "그룹": ["할인 쿠폰군 (A)"] * SIMULATION_MONTHS + ["무료 연장군 (B)"] * SIMULATION_MONTHS,
        "예상 매출액": rev_a + rev_b,
    })

    # 개인별 방어율 분포 (차트용)
    dist_a, dist_b = _build_retention_distributions(sim_df, target_b_df, discount_rate)

    return roi_df, sum(rev_a), sum(rev_b), dist_a, dist_b


# ──────────────────────────────────────────
# 내부 헬퍼: 방어율 분포 데이터 생성
# ──────────────────────────────────────────

def _build_retention_distributions(
    sim_df: pd.DataFrame | None,
    target_b_df: pd.DataFrame | None,
    discount_rate: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    개인별 방어율 분포 DataFrame 반환 (히스토그램 / 산점도용).
    데이터 없으면 빈 DataFrame 반환.
    """
    dist_a = pd.DataFrame()
    dist_b = pd.DataFrame()

    if sim_df is not None and not sim_df.empty and "churn_probability" in sim_df.columns:
        probs = sim_df["churn_probability"].values
        rets  = np.array([calc_individual_retention_a(p, discount_rate) for p in probs])
        dist_a = pd.DataFrame({
            "churn_probability": probs,
            "retention_rate":    rets,
            "group": "A",
        })

    if target_b_df is not None and not target_b_df.empty and "membership_duration_months" in target_b_df.columns:
        durations = target_b_df["membership_duration_months"].values
        rets = np.array([calc_individual_retention_b(m) for m in durations])
        dist_b = pd.DataFrame({
            "membership_duration_months": durations,
            "retention_rate":             rets,
            "group": "B",
        })

    return dist_a, dist_b