import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st

# [중요] 기존 액션 보드 모듈에서 데이터 처리 및 설정 재사용
from pages.action_board.config import HIGH_RISK_THRESHOLD, TWD_TO_KRW, EXPIRY_WINDOW_DAYS, CHURN_REASONS
from pages.action_board.data_layer import get_shifted_raw_data, inject_churn_probability

@st.cache_data
def get_real_action_data(virtual_today):
    """
    실제 DB 데이터를 로드하여 액션 보드 전용 고도화 데이터를 가공합니다.
    """
    raw_result = get_shifted_raw_data()
    if not raw_result or "transactions" not in raw_result:
        return pd.DataFrame()
    
    trans_df = raw_result["transactions"]
    members_df = raw_result.get("members", pd.DataFrame())
    
    # ── 1. 이탈 확률 연동 ──
    # ML 모델이 추론한 실시간 이탈 위험률을 주입합니다.
    prob_df = inject_churn_probability(trans_df)

    # ── 1-1. virtual_today 보정 ──
    # Streamlit date_input 등에서 들어오는 날짜를 pandas datetime으로 통일합니다.
    virtual_today = pd.to_datetime(virtual_today, errors="coerce")

    # membership_expire_date 유효값만 추출
    valid_dates = prob_df["membership_expire_date"].dropna()

    # 날짜 데이터가 전혀 없으면 화면에 표시할 수 없으므로 빈 DataFrame 반환
    if valid_dates.empty:
        return pd.DataFrame()

    min_date = valid_dates.min()
    max_date = valid_dates.max()

    # 선택 날짜가 비정상이거나 데이터 범위를 벗어나면 자동 보정
    if pd.isna(virtual_today) or virtual_today < min_date or virtual_today > max_date:
        virtual_today = max_date - pd.Timedelta(days=3)
    
    # ── 2. 시점 기반 타겟 필터링 ──
    # 분석 기준일(Virtual Today)로부터 만료가 임박한 고객(3일 이내)만 선별합니다.
    window_end = virtual_today + timedelta(days=EXPIRY_WINDOW_DAYS)
    mask_date = (
        (prob_df["membership_expire_date"] >= virtual_today) &
        (prob_df["membership_expire_date"] <= window_end)
    )
    
    # 이탈 확률 0.5 이상의 '위험군' 고객만 액션 대상으로 분류
    candidates = prob_df[mask_date & (prob_df["churn_prob"] >= 0.5)].copy()
    
    # ── 3. 정밀 리스크 등급 부여 ──
    # Churn Prob에 따라 실무에서 사용하는 위험 등급으로 매핑
    candidates["risk_grade"] = candidates["churn_prob"].apply(
        lambda x: "위험도 높음" if x >= HIGH_RISK_THRESHOLD else "위험도 중간"
    )
    
    # ── 4. 이탈 주원인 추론 (Heuristic) ──
    def determine_reason(row):
        if row.get("is_cancel") == 1:
            return "자동결제 해지"
        if row.get("is_auto_renew") == 0:
            return "자동결제 해지"
        return "기타"
    
    candidates["main_reason_code"] = candidates.apply(determine_reason, axis=1)
    
    # ── 5. 기대 추가 수익(plus_price) 정밀 계산 ──
    # 단순 LTV가 아닌 '기대 가치(Expected Value)' 개념 적용.
    # 수식: (연간 예상 매출 * 방어 성공 확률) + 장기 고객 보너스
    # - 방어 성공 확률 = (1 - 이탈 확률) + 알파(마케팅 효과 보정)
    
    # 가입 기간 계산 (Longevity Bonus 적용용)
    if not members_df.empty and "msno" in members_df.columns:
        candidates = pd.merge(
            candidates,
            members_df[["msno", "registration_init_time"]],
            on="msno",
            how="left"
        )
        candidates["reg_date"] = pd.to_datetime(candidates["registration_init_time"], errors="coerce")
        candidates["long_years"] = (virtual_today - candidates["reg_date"]).dt.days / 365
        candidates["long_years"] = candidates["long_years"].fillna(1)
    else:
        candidates["long_years"] = 1.0

    # 최종 기대 추가 수익 계산식 (빡센 버전)
    # (12개월 매출) * (방어 성공 가능성) + (가입연수 * 5000원 충성도 가치)
    candidates["plus_price"] = (
        (candidates["plan_list_price"] * TWD_TO_KRW * 12) * (1.1 - candidates["churn_prob"]) +
        (candidates["long_years"] * 5000)
    ).astype(int)
    
    # ── 6. 필드 선택 및 정리 ──
    candidates.insert(0, "[☑️ 타겟 선택]", False)
    cols = [
        "[☑️ 타겟 선택]", "msno", "churn_prob", "risk_grade", 
        "main_reason_code", "plus_price", "membership_expire_date"
    ]
    
    final_df = candidates[cols].rename(columns={
        "msno": "user_id", 
        "churn_prob": "churn_probability"
    })
    
    return final_df


def apply_filters(df, selected_grades, selected_reasons):
    """
    위험 등급 및 이탈 원인에 따른 정밀 필터링을 수행합니다.
    """
    if df.empty:
        return df
    
    mask = (df['risk_grade'].isin(selected_grades)) & (df['main_reason_code'].isin(selected_reasons))
    return df[mask].copy()

def segment_by_plus_price(df, threshold):
    """
    기대 추가 수익(plus_price) 기준에 따라 VVIP와 일반 고객으로 분리합니다.
    경제적 가치가 높은 고객을 우선 선별할 수 있게 합니다.
    """
    vvip_df = df[df["plus_price"] >= threshold].copy()
    general_df = df[df["plus_price"] < threshold].copy()
    return vvip_df, general_df
