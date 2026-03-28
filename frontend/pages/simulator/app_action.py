import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# [중요] 기존 모듈에서 데이터 처리 로직 재사용
from pages.action_board.config import HIGH_RISK_THRESHOLD, TWD_TO_KRW, EXPIRY_WINDOW_DAYS
from pages.action_board.data_layer import load_raw_data, inject_churn_probability

# ── 세션 상태 초기화 ──
if "vvip_selected" not in st.session_state:
    st.session_state.vvip_selected = False
if "general_selected" not in st.session_state:
    st.session_state.general_selected = False

# ── 페이지 설정 ──
st.title("🎯 고위험군 액션 보드")
st.caption("고객 가치에 따라 그룹을 나누어 맞춤형 마케팅 액션을 시뮬레이션합니다.")

# ==========================================
# 1. 실제 데이터 로드 및 전처리
# ==========================================
@st.cache_data
def get_real_action_data(virtual_today):
    raw_result = load_raw_data()
    if not raw_result or "transactions" not in raw_result:
        st.error("데이터를 불러올 수 없습니다.")
        return pd.DataFrame()
    
    trans_df = raw_result["transactions"]
    prob_df = inject_churn_probability(trans_df)
    
    window_end = virtual_today + timedelta(days=EXPIRY_WINDOW_DAYS)
    mask_date = (prob_df["membership_expire_date"] >= virtual_today) & (prob_df["membership_expire_date"] <= window_end)
    
    candidates = prob_df[mask_date & (prob_df["churn_prob"] >= 0.5)].copy()
    
    candidates["risk_grade"] = candidates["churn_prob"].apply(lambda x: "High" if x >= HIGH_RISK_THRESHOLD else "Medium")
    
    def determine_reason(row):
        if row.get("is_cancel") == 1: return "멤버십 해지"
        if row.get("is_auto_renew") == 0: return "자동결제 미등록"
        return "기타"
    
    candidates["main_reason_code"] = candidates.apply(determine_reason, axis=1)
    candidates["LTV"] = (candidates["plan_list_price"] * TWD_TO_KRW * 12).astype(int)
    candidates.insert(0, "[☑️ 타겟 선택]", False)
    
    cols = ["[☑️ 타겟 선택]", "msno", "churn_prob", "risk_grade", "main_reason_code", "LTV", "membership_expire_date"]
    final_df = candidates[cols].rename(columns={"msno": "user_id", "churn_prob": "churn_probability"})
    
    return final_df

# 사이드바 설정
with st.sidebar:
    st.write("### 📅 시뮬레이션 설정")
    virtual_today_val = st.date_input("분석 기준일", value=datetime.now().date())
    virtual_today = datetime.combine(virtual_today_val, datetime.min.time())

with st.spinner("📦 데이터 분석 중..."):
    target_df = get_real_action_data(virtual_today)

if target_df.empty:
    st.warning("타겟 유저가 없습니다.")
    st.stop()

# ==========================================
# 2. 상단: 전체 필터링
# ==========================================
st.write("### ⚙️ 공통 필터")
f_col1, f_col2 = st.columns(2)
with f_col1:
    selected_grades = st.multiselect("위험 등급", options=['High', 'Medium'], default=['High', 'Medium'])
with f_col2:
    selected_reasons = st.multiselect("이탈 원인", options=target_df['main_reason_code'].unique(), default=target_df['main_reason_code'].unique())

mask = (target_df['risk_grade'].isin(selected_grades)) & (target_df['main_reason_code'].isin(selected_reasons))
filtered_df = target_df[mask].copy()

# ==========================================
# 3. 중단: LTV 기반 그룹 세그먼트 (VVIP vs General)
# ==========================================
LTV_THRESHOLD = 50000
vvip_df = filtered_df[filtered_df["LTV"] >= LTV_THRESHOLD].copy()
general_df = filtered_df[filtered_df["LTV"] < LTV_THRESHOLD].copy()

tab_vvip, tab_general = st.tabs([f"💎 우량 고객 ({len(vvip_df)}명)", f"🌱 일반/신규 고객 ({len(general_df)}명)"])

# ── [탭 1: VVIP] ──────────────────────────────────────────
with tab_vvip:
    if len(vvip_df) > 0:
        c1, c2, _ = st.columns([1, 1, 4])
        if c1.button("✅ 전체 선택", key="btn_vvip_all"):
            st.session_state.vvip_selected = True
            st.rerun()
        if c2.button("⭕ 선택 해제", key="btn_vvip_none"):
            st.session_state.vvip_selected = False
            st.rerun()
        
        vvip_df["[☑️ 타겟 선택]"] = st.session_state.vvip_selected
        
        # ID 마스킹 및 출력
        vvip_display = vvip_df.copy()
        vvip_display['user_id'] = vvip_display['user_id'].apply(lambda x: x[:10] + ".." if isinstance(x, str) else x)
        
        vvip_edit = st.data_editor(vvip_display, hide_index=True, key="editor_vvip", use_container_width=True,
                                  column_config={"churn_probability": st.column_config.ProgressColumn("이탈 확률", format="%.2f", min_value=0, max_value=1),
                                                 "LTV": st.column_config.NumberColumn("기대 LTV", format="₩%d")})
        
        # VVIP 전용 액션 버튼
        v_sel = vvip_edit[vvip_edit["[☑️ 타겟 선택]"] == True]
        if len(v_sel) > 0:
            a_col1, a_col2 = st.columns([1, 3])
            if a_col1.button("⏳ 30일 무료 연장권 발송", type="primary", key="act_vvip"):
                st.balloons()
                st.success(f"VVIP {len(v_sel)}명에게 무료 연장권이 발송되었습니다!")
    else:
        st.info("조건에 맞는 VVIP 고객이 없습니다.")

# ── [탭 2: General] ───────────────────────────────────────
with tab_general:
    if len(general_df) > 0:
        c1, c2, _ = st.columns([1, 1, 4])
        if c1.button("✅ 전체 선택", key="btn_gen_all"):
            st.session_state.general_selected = True
            st.rerun()
        if c2.button("⭕ 선택 해제", key="btn_gen_none"):
            st.session_state.general_selected = False
            st.rerun()
            
        general_df["[☑️ 타겟 선택]"] = st.session_state.general_selected
        
        gen_display = general_df.copy()
        gen_display['user_id'] = gen_display['user_id'].apply(lambda x: x[:10] + ".." if isinstance(x, str) else x)
        
        gen_edit = st.data_editor(gen_display, hide_index=True, key="editor_gen", use_container_width=True,
                                 column_config={"churn_probability": st.column_config.ProgressColumn("이탈 확률", format="%.2f", min_value=0, max_value=1),
                                                "LTV": st.column_config.NumberColumn("기대 LTV", format="₩%d")})
        
        # 일반 전용 액션 버튼
        g_sel = gen_edit[gen_edit["[☑️ 타겟 선택]"] == True]
        if len(g_sel) > 0:
            a_col1, a_col2 = st.columns([1, 3])
            if a_col1.button("🎁 50% 할인 쿠폰 발송", type="primary", key="act_gen"):
                st.balloons()
                st.success(f"일반 고객 {len(g_sel)}명에게 할인 쿠폰이 발송되었습니다!")
    else:
        st.info("조건에 맞는 일반 고객이 없습니다.")