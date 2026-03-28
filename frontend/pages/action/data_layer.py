import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st

# [중요] 기존 액션 보드 모듈에서 데이터 처리 및 설정 재사용
from pages.action_board.config import HIGH_RISK_THRESHOLD, TWD_TO_KRW, EXPIRY_WINDOW_DAYS
from pages.action_board.data_layer import load_raw_data, inject_churn_probability

@st.cache_data
def get_real_action_data(virtual_today):
    """
    실제 CSV 데이터를 로드하여 액션 보드용 데이터를 가공합니다.
    """
    raw_result = load_raw_data()
    if not raw_result or "transactions" not in raw_result:
        return pd.DataFrame()
    
    trans_df = raw_result["transactions"]
    prob_df = inject_churn_probability(trans_df)
    
    # 필터링 (분석 기준일 기준 만료 임박)
    window_end = virtual_today + timedelta(days=EXPIRY_WINDOW_DAYS)
    mask_date = (prob_df["membership_expire_date"] >= virtual_today) & (prob_df["membership_expire_date"] <= window_end)
    
    # 이탈 확률 0.5 이상의 잠재적 타겟 유저 선별
    candidates = prob_df[mask_date & (prob_df["churn_prob"] >= 0.5)].copy()
    
    # 1. 리스크 등급 부여
    candidates["risk_grade"] = candidates["churn_prob"].apply(lambda x: "위험도 높음" if x >= HIGH_RISK_THRESHOLD else "위험도 중간")
    
    # 2. 이탈 원인 부여
    def determine_reason(row):
        if row.get("is_cancel") == 1: return "멤버십 해지"
        if row.get("is_auto_renew") == 0: return "자동결제 미등록"
        return "기타"
    
    candidates["main_reason_code"] = candidates.apply(determine_reason, axis=1)
    
    # 3. 계산
    candidates["plus_price"] = (candidates["plan_list_price"] * TWD_TO_KRW * 12).astype(int)
    
    # 4. 필드 선택 및 정리
    candidates.insert(0, "[☑️ 타겟 선택]", False)
    cols = ["[☑️ 타겟 선택]", "msno", "churn_prob", "risk_grade", "main_reason_code", "plus_price", "membership_expire_date"]
    
    final_df = candidates[cols].rename(columns={"msno": "user_id", "churn_prob": "churn_probability"})
    
    return final_df

def apply_filters(df, selected_grades, selected_reasons):
    """
    위험 등급 및 이탈 원인에 따른 필터링을 수행합니다.
    """
    if df.empty:
        return df
    
    mask = (df['risk_grade'].isin(selected_grades)) & (df['main_reason_code'].isin(selected_reasons))
    return df[mask].copy()

def segment_by_plus_price(df, threshold):
    """
    plus_price 기준에 따라 VVIP와 일반 고객으로 분리합니다.
    """
    vvip_df = df[df["plus_price"] >= threshold].copy()
    general_df = df[df["plus_price"] < threshold].copy()
    return vvip_df, general_df
