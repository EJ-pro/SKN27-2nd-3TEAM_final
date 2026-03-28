import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st

# [중요] 기존 액션 보드 모듈에서 데이터 처리 및 설정 재사용
from pages.action_board.config import HIGH_RISK_THRESHOLD, TWD_TO_KRW, EXPIRY_WINDOW_DAYS
from pages.action_board.data_layer import load_raw_data, inject_churn_probability
from pages.simulator.config import A_BASE_RETENTION, A_RETENTION_FACTOR, B_FIXED_RETENTION

@st.cache_data
def get_real_sim_data(virtual_today):
    """
    실제 CSV 데이터를 로드하여 분석 기준일 기준의 고위험군 유저 풀을 생성합니다.
    """
    raw_result = load_raw_data()
    if not raw_result or "transactions" not in raw_result:
        return pd.DataFrame()
    
    trans_df = raw_result["transactions"]
    prob_df = inject_churn_probability(trans_df)
    
    # 분석 기준일로부터 만료 임박한 유저 필터링
    window_end = virtual_today + timedelta(days=EXPIRY_WINDOW_DAYS)
    mask_date = (prob_df["membership_expire_date"] >= virtual_today) & (prob_df["membership_expire_date"] <= window_end)
    
    # 이탈 확률 0.5 이상의 잠재적 타겟 유저 선별
    candidates = prob_df[mask_date & (prob_df["churn_prob"] >= 0.5)].copy()
    
    # 필드 정리 및 시뮬레이션용 데이터 가공
    candidates = candidates.rename(columns={"msno": "user_id", "churn_prob": "churn_probability"})
    
    # 가입 기간 (간이 계산용 시뮬레이션 필드)
    rng = np.random.default_rng(42)
    candidates["membership_duration_months"] = rng.integers(1, 13, len(candidates))
    
    return candidates

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
    # 월별 수익 리스트 (TWD -> KRW 환산 적용)
    rev_a = [
        (target_a_count * retention_a) * (avg_price * (1 - discount_rate/100)) * TWD_TO_KRW, # 1월
        (target_a_count * retention_a) * avg_price * TWD_TO_KRW,                            # 2월
        (target_a_count * retention_a) * avg_price * TWD_TO_KRW                             # 3월
    ]
    
    rev_b = [
        (target_b_count * retention_b) * 0,                                                 # 1월 (무료)
        (target_b_count * retention_b) * avg_price * TWD_TO_KRW,                            # 2월
        (target_b_count * retention_b) * avg_price * TWD_TO_KRW                             # 3월
    ]
    
    roi_df = pd.DataFrame({
        "Month": ["1개월 후", "2개월 후", "3개월 후"] * 2,
        "Group": ["Group A"] * 3 + ["Group B"] * 3,
        "Revenue": rev_a + rev_b
    })
    
    return roi_df, sum(rev_a), sum(rev_b)
