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
    get_real_sim_data, calculate_retention_rates, calculate_roi_data,
    get_simulator_default_date
)
from pages.action_board.config import TWD_TO_KRW

# ── 페이지 설정 ──
st.set_page_config(page_title="마케팅 성과 시뮬레이터 🌸", layout="wide")

# ── 벚꽃 + 초록 봄 테마 CSS ──────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');

:root {
    --sakura-50:  #FFF0F5;
    --sakura-100: #FFD6E7;
    --sakura-200: #FFB3D1;
    --sakura-400: #F472A8;
    --sakura-600: #C94E80;
    --sakura-800: #8B2255;
    --green-50:   #F0FAF0;
    --green-100:  #C8EDC0;
    --green-200:  #97D47F;
    --green-400:  #55A83A;
    --green-600:  #2E7D1A;
    --green-800:  #16500A;
}

html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif !important;
}

/* 전체 배경 */
.stApp {
    background: linear-gradient(135deg, #FFF8FB 0%, #F6FBF4 100%) !important;
}

/* 사이드바 */
[data-testid="stSidebar"] {
    background: var(--sakura-50) !important;
    border-right: 1px solid var(--sakura-200) !important;
}
[data-testid="stSidebar"] * { color: var(--sakura-800) !important; }

/* 타이틀 */
h1 {
    font-size: 2rem !important;
    color: var(--sakura-800) !important;
    border-bottom: 3px solid;
    border-image: linear-gradient(90deg, #FFB3D1, #F472A8, #55A83A, #97D47F) 1;
    padding-bottom: 0.4rem;
}

/* 서브헤더 h2 */
h2 {
    color: var(--sakura-800) !important;
    font-size: 1.1rem !important;
    font-weight: 600 !important;
}

/* h3, h4 섹션 타이틀 */
h3, h4 {
    color: var(--green-800) !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
}

/* 캡션 */
.stApp [data-testid="stCaptionContainer"] p {
    color: var(--sakura-600) !important;
    font-size: 0.82rem;
}

/* 구분선 */
hr, [data-testid="stDivider"] {
    border: none !important;
    height: 2px !important;
    background: linear-gradient(90deg, var(--sakura-200), var(--sakura-400), var(--green-400), var(--green-200)) !important;
    margin: 0.75rem 0 1.25rem !important;
    opacity: 1 !important;
}

/* number_input */
[data-testid="stNumberInput"] input {
    border-color: var(--sakura-200) !important;
    border-radius: 9px !important;
}
[data-testid="stNumberInput"] input:focus {
    border-color: var(--sakura-400) !important;
    box-shadow: 0 0 0 3px rgba(244,114,168,0.15) !important;
}

/* 슬라이더 */
[data-testid="stSlider"] > div > div > div {
    background: var(--sakura-400) !important;
}
[data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
    background: var(--sakura-400) !important;
    border-color: var(--sakura-400) !important;
}

/* selectbox */
[data-testid="stSelectbox"] > div > div {
    border-color: var(--green-200) !important;
    border-radius: 9px !important;
}
[data-testid="stSelectbox"] > div > div:focus-within {
    border-color: var(--green-400) !important;
    box-shadow: 0 0 0 3px rgba(85,168,58,0.15) !important;
}

/* radio */
[data-testid="stRadio"] label {
    color: var(--sakura-800) !important;
    font-size: 0.88rem !important;
}
[data-testid="stRadio"] [data-baseweb="radio"] div {
    border-color: var(--sakura-400) !important;
}
[data-testid="stRadio"] [data-baseweb="radio"] [data-checked="true"] div {
    background: var(--sakura-400) !important;
    border-color: var(--sakura-400) !important;
}

/* info 박스 */
[data-testid="stAlert"][data-type="info"] {
    background: var(--sakura-50) !important;
    border-left: 4px solid var(--sakura-400) !important;
    border-radius: 12px !important;
    color: var(--sakura-800) !important;
}
[data-testid="stAlert"][data-type="info"] p {
    color: var(--sakura-800) !important;
}

/* success 박스 */
[data-testid="stAlert"][data-type="success"] {
    background: var(--green-50) !important;
    border-left: 4px solid var(--green-400) !important;
    border-radius: 12px !important;
}
[data-testid="stAlert"][data-type="success"] p {
    color: var(--green-800) !important;
}

/* error 박스 */
[data-testid="stAlert"][data-type="error"] {
    border-radius: 12px !important;
}

/* dataframe */
[data-testid="stDataFrame"] {
    border: 0.5px solid var(--sakura-100) !important;
    border-radius: 10px !important;
    overflow: hidden;
}
[data-testid="stDataFrame"] th {
    background: var(--sakura-50) !important;
    color: var(--sakura-800) !important;
}

/* Plotly 차트 컨테이너 */
[data-testid="stPlotlyChart"] {
    background: white !important;
    border: 0.5px solid var(--sakura-100) !important;
    border-radius: 14px !important;
    padding: 0.5rem !important;
    box-shadow: 0 2px 12px rgba(244,114,168,0.05) !important;
}

/* 스피너 */
[data-testid="stSpinner"] { color: var(--sakura-400) !important; }
</style>
""", unsafe_allow_html=True)


# ── 타이틀 ──
st.markdown("🌸 &nbsp; **봄**", unsafe_allow_html=True)
st.title("📈 마케팅 성과 시뮬레이터")
st.caption("실제 고객 데이터를 기반으로 캠페인 전략별 예상 이탈 방어율을 비교 분석합니다.")


# ==========================================
# 0. 사이드바 및 데이터 로드
# ==========================================
with st.sidebar:
    st.markdown("### 📅 시뮬레이션 설정")
    default_date = get_simulator_default_date()
    virtual_today = datetime.combine(default_date, datetime.min.time())
    st.markdown("---")
    st.markdown(
        "<small style='color:#C94E80'>🌸 봄 시즌 리텐션 캠페인</small>",
        unsafe_allow_html=True,
    )

with st.spinner("🌸 실제 고객 데이터 분석 중..."):
    sim_df = get_real_sim_data(virtual_today)

    if sim_df.empty:
        st.error("데이터 분석 실패: 조건에 맞는 고객을 찾을 수 없습니다.")
        st.stop()


# ==========================================
# 1. 상단: 캠페인 그룹 설정
# ==========================================
st.markdown("<hr>", unsafe_allow_html=True)
config_col1, config_col2, config_col3 = st.columns([2, 2, 1.5], gap="large")

total_pool_size = len(sim_df)

with config_col1:
    st.subheader("🅰️ Group A: 할인 쿠폰")
    target_a_count = st.number_input(
        "타겟 유저 수 (A)",
        min_value=1, max_value=total_pool_size,
        value=min(DEFAULT_A_TARGET_COUNT, total_pool_size), key="n_a",
    )
    discount_rate = st.slider("할인율 (%)", 0, 100, 20, step=5, key="d_a")

    ret_a, ret_b = calculate_retention_rates(discount_rate)
    st.info(f"💡 예상 방어 성공률: **{ret_a*100:.1f}%**")

with config_col2:
    st.subheader("🅱️ Group B: 무료 연장")
    filter_option = st.selectbox(
        "타겟 필터링 조건 (B)",
        options=FILTER_OPTIONS_B,
        index=1,
    )

    months_limit  = int(filter_option.split("개월")[0])
    target_b_df   = sim_df[sim_df["membership_duration_months"] >= months_limit]
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

    display_df = view_df[["user_id", "churn_probability"]].copy()
    display_df["user_id"] = display_df["user_id"].apply(
        lambda x: x[:10] + ".." if isinstance(x, str) else x
    )
    st.dataframe(display_df.head(100), height=200, use_container_width=True)


# ==========================================
# 2. 중단: 시뮬레이션 결과 차트
# ==========================================
st.markdown("<hr>", unsafe_allow_html=True)
st.write(f"### 📊 성과 예측 (분석일: {virtual_today})")
chart_col1, chart_col2, chart_col3 = st.columns([1, 1, 2])

SPRING_COLOR_A = "#F472A8"   # 벚꽃 핑크  (Group A)
SPRING_COLOR_B = "#55A83A"   # 새싹 그린  (Group B)
SPRING_GRAY    = "#D3D1C7"   # 연회색     (실패)

def create_donut(rate, title, color):
    fig = px.pie(
        values=[rate, 1 - rate],
        names=["방어 성공", "실패"],
        hole=0.6,
        color_discrete_sequence=[color, SPRING_GRAY],
        title=title,
    )
    fig.update_layout(
        showlegend=False,
        height=300,
        margin=dict(t=40, b=0, l=0, r=0),
        paper_bgcolor="white",
        font=dict(family="Noto Sans KR", color="#8B2255"),
    )
    return fig

with chart_col1:
    st.plotly_chart(create_donut(ret_a, "Group A 성공률", SPRING_COLOR_A), use_container_width=True)

with chart_col2:
    st.plotly_chart(create_donut(ret_b, "Group B 성공률", SPRING_COLOR_B), use_container_width=True)

with chart_col3:
    avg_price = sim_df["plan_list_price"].mean() if not sim_df.empty else 149
    roi_df, total_rev_a, total_rev_b = calculate_roi_data(
        target_a_count, target_b_count, ret_a, ret_b, discount_rate, avg_price
    )

    fig_rev = px.bar(
        roi_df, x="Month", y="Revenue", color="Group",
        barmode="group",
        title="예상 수익 추이 (원화 환산)",
        color_discrete_map={"Group A": SPRING_COLOR_A, "Group B": SPRING_COLOR_B},
        template="plotly_white",
    )
    fig_rev.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Noto Sans KR", color="#8B2255"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=50, b=10, l=10, r=10),
    )
    fig_rev.update_traces(marker_line_width=0)
    st.plotly_chart(fig_rev, use_container_width=True)


# ==========================================
# 3. 하단: 시뮬레이션 결론
# ==========================================
st.markdown("<hr>", unsafe_allow_html=True)
better_group = "A" if total_rev_a > total_rev_b else "B"
diff_rev     = abs(total_rev_a - total_rev_b)

st.write("#### 🛡️ 시뮬레이션 결론")
if better_group == "A":
    st.success(
        f"🟢 **결론**: Group B(무료 연장)가 초기 방어율은 일정하게 유지되나, "
        f"**A그룹(할인 쿠폰)이 단기 수익 회수가 빠르고 3개월 누적 수익이 약 {diff_rev:,.0f}원 더 높습니다.**"
    )
else:
    st.info(
        f"🔵 **결론**: Group A(할인)는 초기 매출 감소가 크지만, "
        f"**B그룹(무료 연장)이 첫 달 매출 공백을 감수하더라도 고객 유지 효과로 "
        f"3개월 누적 수익 약 {diff_rev:,.0f}원만큼 더 유리해집니다.**"
    )

st.caption(
    f"※ 본 시뮬레이션은 실제 고객 {total_pool_size}명을 기반으로 계산되었으며, "
    f"환율 1 TWD = {TWD_TO_KRW}원이 적용되었습니다."
)