import streamlit as st
import pandas as pd
from datetime import datetime

# [모듈화] 전용 설정 및 데이터 레이어 임포트
from pages.action.config import (
    PLUS_PRICE_THRESHOLD, RISK_GRADES, VVIP_ACTION_TEXT, 
    GENERAL_ACTION_TEXT, VVIP_SUCCESS_MSG, GENERAL_SUCCESS_MSG
)
from pages.action.data_layer import get_real_action_data, apply_filters, segment_by_plus_price

# ── 세션 상태 초기화 ──
if "vvip_selected" not in st.session_state:
    st.session_state.vvip_selected = False
if "general_selected" not in st.session_state:
    st.session_state.general_selected = False

# ── 페이지 설정 ──
st.title("🎯 고위험군 액션 보드")
st.caption("고객 가치에 따라 그룹을 나누어 맞춤형 마케팅 액션을 시뮬레이션합니다.")

# ==========================================
# 1. 사이드바 및 데이터 로드
# ==========================================
with st.sidebar:
    st.write("### 📅 시뮬레이션 설정")
    virtual_today_val = st.date_input("분석 기준일", value=datetime.now().date())
    virtual_today = datetime.combine(virtual_today_val, datetime.min.time())

with st.spinner("📦 데이터 분석 중..."):
    target_df = get_real_action_data(virtual_today)

if target_df.empty:
    st.warning("분석일 기준 만료 예정인 고위험 유저가 없습니다.")
    st.stop()

# ==========================================
# 2. 상단: 공통 필터링
# ==========================================
st.write("### ⚙️ 공통 필터")
f_col1, f_col2 = st.columns(2)
with f_col1:
    selected_grades = st.multiselect("위험 등급", options=RISK_GRADES, default=RISK_GRADES)
with f_col2:
    all_reasons = sorted(target_df['main_reason_code'].unique())
    selected_reasons = st.multiselect("이탈 원인", options=all_reasons, default=all_reasons)

filtered_df = apply_filters(target_df, selected_grades, selected_reasons)

# ==========================================
# 3. 중단: plus_price 기반 그룹
# ==========================================
vvip_df, general_df = segment_by_plus_price(filtered_df, PLUS_PRICE_THRESHOLD)

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
        
        # ID 마스킹 (UX)
        vvip_display = vvip_df.copy()
        vvip_display['user_id'] = vvip_display['user_id'].apply(lambda x: x[:10] + ".." if isinstance(x, str) else x)
        
        vvip_edit = st.data_editor(
            vvip_display, hide_index=True, key="editor_vvip", use_container_width=True,
            column_config={
                "churn_probability": st.column_config.ProgressColumn("이탈 확률", format="%.2f", min_value=0, max_value=1),
                "plus_price": st.column_config.NumberColumn("기대 추가 수익", format="₩%d"),
                "membership_expire_date": st.column_config.DateColumn("만료일")
            }
        )
        
        v_sel = vvip_edit[vvip_edit["[☑️ 타겟 선택]"] == True]
        if len(v_sel) > 0:
            a_col1, a_col2 = st.columns([1, 3])
            if a_col1.button(VVIP_ACTION_TEXT, type="primary", key="act_vvip"):
                # 이거 끄시면 풍선안나옵니다
                st.balloons()
                st.success(VVIP_SUCCESS_MSG.format(len(v_sel)))
    else:
        st.info("조건에 맞는 우량 고객이 없습니다.")

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
        
        gen_edit = st.data_editor(
            gen_display, hide_index=True, key="editor_gen", use_container_width=True,
            column_config={
                "churn_probability": st.column_config.ProgressColumn("이탈 확률", format="%.2f", min_value=0, max_value=1),
                "plus_price": st.column_config.NumberColumn("기대 추가수익", format="₩%d"),
                "membership_expire_date": st.column_config.DateColumn("만료일")
            }
        )
        
        g_sel = gen_edit[gen_edit["[☑️ 타겟 선택]"] == True]
        if len(g_sel) > 0:
            a_col1, a_col2 = st.columns([1, 3])
            if a_col1.button(GENERAL_ACTION_TEXT, type="primary", key="act_gen"):
                # 이거 끄시면 풍선안나옵니다
                st.balloons()
                st.success(GENERAL_SUCCESS_MSG.format(len(g_sel)))
    else:
        st.info("조건에 맞는 일반 고객이 없습니다.")