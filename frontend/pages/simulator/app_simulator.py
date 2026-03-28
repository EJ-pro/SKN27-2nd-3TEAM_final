import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# [모듈화] 전용 설정 및 데이터 레이어 임포트
from pages.simulator.config import (
    COLOR_GROUP_A, COLOR_GROUP_B, COLOR_GRAY,
    DEFAULT_A_TARGET_COUNT, FILTER_OPTIONS_B
)
from pages.simulator.data_layer import (
    get_real_sim_data, calculate_retention_rates, calculate_roi_data
)
from pages.action_board.config import TWD_TO_KRW

# ── 페이지 설정 ──
st.title("📈 마케팅 성과 시뮬레이터")
st.caption("실제 고객 데이터를 기반으로 캠페인 전략별 예상 이탈 방어율을 비교 분석합니다.")

# ==========================================
# 0. 사이드바 및 데이터 로드
# ==========================================
with st.sidebar:
    st.write("### 📅 시뮬레이션 설정")
    virtual_today_val = st.date_input("분석 기준일 (Virtual Today)", value=datetime.now().date())
    virtual_today = datetime.combine(virtual_today_val, datetime.min.time())

with st.spinner("📦 실제 고객 데이터 분석 중..."):
    sim_df = get_real_sim_data(virtual_today)

if sim_df.empty:
    st.warning("분석 기준일 기준, 시뮬레이션을 진행할 타겟 유저가 부족합니다. 다른 날짜를 선택해 주세요.")
    st.stop()

# ==========================================
# 1. 상단: 캠페인 그룹 설정
# ==========================================
st.divider()
config_col1, config_col2, config_col3 = st.columns([2, 2, 1.5], gap="large")

total_pool_size = len(sim_df)

with config_col1:
    st.subheader("🅰️ Group A: 할인 쿠폰")
    target_a_count = st.number_input(
        "타겟 유저 수 (A)", 
        min_value=1, max_value=total_pool_size, 
        value=min(DEFAULT_A_TARGET_COUNT, total_pool_size), key="n_a"
    )
    discount_rate = st.slider("할인율 (%)", 0, 100, 20, step=5, key="d_a")
    
    ret_a, ret_b = calculate_retention_rates(discount_rate)
    st.info(f"💡 예상 방어 성공률: **{ret_a*100:.1f}%**")

with config_col2:
    st.subheader("🅱️ Group B: 무료 연장")
    filter_option = st.selectbox(
        "타겟 필터링 조건 (B)",
        options=FILTER_OPTIONS_B,
        index=1
    )
    
    months_limit = int(filter_option.split("개월")[0])
    target_b_df = sim_df[sim_df["membership_duration_months"] >= months_limit]
    target_b_count = len(target_b_df)
    
    st.write(f"👥 실제 필터링된 타겟: **{target_b_count}명**")
    st.info(f"💡 예상 방어 성공률: **{ret_b*100:.1f}%**")

with config_col3:
    st.subheader("🔍 대상 데이터 조회")
    group_view = st.radio("그룹 선택", ["Group A", "Group B"], horizontal=True)
    
    view_df = (
        sim_df.sort_values("churn_probability", ascending=False).head(target_a_count)
        if group_view == "Group A" else target_b_df
    )
    
    # ID 마스킹 (UX)
    display_df = view_df[["user_id", "churn_probability"]].copy()
    display_df["user_id"] = display_df["user_id"].apply(lambda x: x[:10] + ".." if isinstance(x, str) else x)
    st.dataframe(display_df.head(100), height=200, use_container_width=True)

# ==========================================
# 2. 중단: 시뮬레이션 결과 차트
# ==========================================
st.divider()
st.write(f"### 📊 성과 예측 (분석일: {virtual_today_val})")
chart_col1, chart_col2, chart_col3 = st.columns([1, 1, 2])

def create_donut(rate, title, color):
    fig = px.pie(
        values=[rate, 1-rate], 
        names=["방어 성공", "실패"],
        hole=0.6,
        color_discrete_sequence=[color, COLOR_GRAY],
        title=title
    )
    fig.update_layout(showlegend=False, height=300, margin=dict(t=40, b=0, l=0, r=0))
    return fig

with chart_col1:
    st.plotly_chart(create_donut(ret_a, "Group A 성공률", COLOR_GROUP_A), use_container_width=True)

with chart_col2:
    st.plotly_chart(create_donut(ret_b, "Group B 성공률", COLOR_GROUP_B), use_container_width=True)

with chart_col3:
    avg_price = sim_df["plan_list_price"].mean() if not sim_df.empty else 149
    roi_df, total_rev_a, total_rev_b = calculate_roi_data(
        target_a_count, target_b_count, ret_a, ret_b, discount_rate, avg_price
    )
    
    fig_rev = px.bar(
        roi_df, x="Month", y="Revenue", color="Group",
        barmode="group", title="예상 수익 추이 (원화 환산)",
        color_discrete_map={"Group A": COLOR_GROUP_A, "Group B": COLOR_GROUP_B}
    )
    st.plotly_chart(fig_rev, use_container_width=True)

# ==========================================
# 3. 하단: 시뮬레이션 결론
# ==========================================
st.divider()
better_group = "A" if total_rev_a > total_rev_b else "B"
diff_rev = abs(total_rev_a - total_rev_b)

st.write("#### 🛡️ 시뮬레이션 결론")
if better_group == "A":
    st.success(f"🟢 **결론**: Group B(무료 연장)가 초기 방어율은 일정하게 유지되나, **A그룹(할인 쿠폰)이 단기 수익 회수가 빠르고 3개월 누적 수익이 약 {diff_rev:,.0f}원 더 높습니다.**")
else:
    st.info(f"🔵 **결론**: Group A(할인)는 초기 매출 감소가 크지만, **B그룹(무료 연장)이 첫 달 매출 공백을 감수하더라도 고객 유지 효과로 3개월 누적 수익 약 {diff_rev:,.0f}원만큼 더 유리해집니다.**")

st.caption(f"※ 본 시뮬레이션은 실제 고객 {total_pool_size}명을 기반으로 계산되었으며, 환율 1 TWD = {TWD_TO_KRW}원이 적용되었습니다.")
