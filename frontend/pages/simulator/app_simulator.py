import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

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

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');

:root {
    --sk-50:  #FFF0F5;
    --sk-100: #FFD6E7;
    --sk-200: #FFB3D1;
    --sk-400: #F472A8;
    --sk-600: #C94E80;
    --sk-800: #8B2255;
    --gn-50:  #F0FAF0;
    --gn-100: #C8EDC0;
    --gn-200: #97D47F;
    --gn-400: #55A83A;
    --gn-600: #2E7D1A;
    --gn-800: #16500A;
    --radius: 14px;
    --shadow-pink:  0 4px 18px rgba(244,114,168,0.10);
    --shadow-green: 0 4px 18px rgba(85,168,58,0.10);
}

html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif !important; }
.stApp { background: linear-gradient(150deg, #FFF8FB 0%, #F6FBF4 100%) !important; }
header[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stDeploymentButton"],
[data-testid="stMainMenu"] { visibility: hidden; }
h1, h2, h3, h4 { margin-top: 0 !important; }

/* ── 사이드바 ── */
[data-testid="stSidebar"] {
    background: var(--sk-50) !important;
    border-right: 1.5px solid var(--sk-200) !important;
}
[data-testid="stSidebar"] * { color: var(--sk-800) !important; }
[data-testid="stSidebar"] [data-testid="stDateInput"] input {
    border-color: var(--sk-200) !important;
    border-radius: 9px !important;
    background: white !important;
}

/* ── 페이지 헤더 배너 ── */
.page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: white;
    border: 1px solid var(--sk-100);
    border-left: 5px solid var(--sk-400);
    border-radius: var(--radius);
    padding: 1rem 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: var(--shadow-pink);
}
.page-header-title {
    font-size: 1.45rem;
    font-weight: 700;
    color: var(--sk-800);
    margin: 0;
    line-height: 1.3;
}
.page-header-sub {
    font-size: 0.78rem;
    color: var(--sk-600);
    margin-top: 0.2rem;
}
.page-header-badge {
    font-size: 0.75rem;
    font-weight: 600;
    background: var(--sk-100);
    color: var(--sk-800);
    border: 1px solid var(--sk-200);
    border-radius: 20px;
    padding: 5px 14px;
    white-space: nowrap;
}

/* ── 섹션 타이틀 ── */
.section-title {
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: var(--sk-600);
    border-left: 3px solid var(--sk-400);
    padding-left: 0.6rem;
    margin: 0 0 1rem 0;
}

/* ── 구분선 ── */
.divider {
    height: 2px;
    background: linear-gradient(90deg, var(--sk-200), var(--sk-400), var(--gn-400), var(--gn-200));
    border: none;
    border-radius: 2px;
    margin: 1.75rem 0;
    opacity: 1;
}

/* ── 그룹 카드 (Container Hack) ── */
div[data-testid="stVerticalBlock"]:has(> div.card-pink) {
    background: white;
    border: 1px solid var(--sk-100);
    border-top: 4px solid var(--sk-400);
    border-radius: var(--radius);
    padding: 1rem 1.5rem 1.5rem;
    box-shadow: var(--shadow-pink);
}
div[data-testid="stVerticalBlock"]:has(> div.card-green) {
    background: white;
    border: 1px solid var(--gn-100);
    border-top: 4px solid var(--gn-400);
    border-radius: var(--radius);
    padding: 1rem 1.5rem 1.5rem;
    box-shadow: var(--shadow-green);
}

/* ── 카드 칩 ── */
.card-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    padding: 4px 12px;
    border-radius: 20px;
    margin-bottom: 1rem;
}
.card-chip.pink  { background: var(--sk-100);  color: var(--sk-800);  border: 1px solid var(--sk-200); }
.card-chip.green { background: var(--gn-100); color: var(--gn-800); border: 1px solid var(--gn-200); }

/* ── 타겟 수 뱃지 (자동계산) ── */
.target-auto-badge {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.55rem 1rem;
    border-radius: 10px;
    font-size: 0.83rem;
    margin-bottom: 0.9rem;
}
.target-auto-badge.pink  { background: var(--sk-50);  border: 1px solid var(--sk-200); color: var(--sk-800); }
.target-auto-badge.green { background: var(--gn-50); border: 1px solid var(--gn-200); color: var(--gn-800); }
.target-auto-badge span.label { font-weight: 500; }
.target-auto-badge span.value { font-weight: 700; font-size: 1rem; }

/* ── 슬라이더 ── */
[data-testid="stSlider"] > div > div > div { background: var(--sk-400) !important; }
[data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
    background: var(--sk-400) !important;
    border-color: var(--sk-400) !important;
}
/* 슬라이더 현재값 숫자 (thumb 아래 텍스트) */
[data-testid="stSlider"] [data-testid="stTickBarMin"],
[data-testid="stSlider"] [data-testid="stTickBarMax"] {
    color: var(--sk-600) !important;
    font-size: 0.75rem !important;
}
/* ── 슬라이더 현재값 (상시 노출 배지) ── */
div[data-testid="stSliderValue"] {
    color: var(--sk-800) !important;
    font-size: 0.85rem !important;
    font-weight: 700 !important;
    background: var(--sk-100) !important;
    border: 1px solid var(--sk-200) !important;
    border-radius: 8px !important;
    padding: 2px 10px !important;
    margin-bottom: 6px !important;
    visibility: visible !important;
    opacity: 1 !important;
    display: inline-block !important;
}

/* 슬라이더 라벨 (타이틀) */
[data-testid="stSlider"] label p {
    color: var(--sk-800) !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
}

/* ── 예상 방어 성공률 뱃지 ── */
.rate-badge {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0.65rem 1rem;
    border-radius: 10px;
    font-size: 0.83rem;
    font-weight: 600;
    margin-top: 0.9rem;
    margin-bottom: 0;  /* expander와 간격은 아래 spacer로 */
}
.rate-badge.pink  { background: var(--sk-50);  border: 1px solid var(--sk-200); color: var(--sk-800); }
.rate-badge.green { background: var(--gn-50); border: 1px solid var(--gn-200); color: var(--gn-800); }

/* ── expander 위 여백 ── */
.expander-spacer { margin-top: 1.5rem; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background: white !important;
    border: 1px solid var(--sk-100) !important;
    border-left: 3px solid var(--sk-200) !important;
    border-radius: 10px !important;
}
[data-testid="stExpander"] summary {
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    color: var(--sk-800) !important;
}

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {
    border-color: var(--gn-200) !important;
    border-radius: 9px !important;
}
[data-testid="stSelectbox"] > div > div:focus-within {
    border-color: var(--gn-400) !important;
    box-shadow: 0 0 0 3px rgba(85,168,58,0.12) !important;
}

/* ── Radio ── */
[data-testid="stRadio"] label { color: var(--sk-800) !important; font-size: 0.85rem !important; }

/* ── KPI 카드 ── */
[data-testid="stMetric"] {
    background: white !important;
    border: 1px solid var(--sk-100) !important;
    border-top: 3px solid var(--sk-400) !important;
    border-radius: var(--radius) !important;
    padding: 1.1rem 1rem !important;
    box-shadow: var(--shadow-pink) !important;
    text-align: center !important;
    transition: transform 0.15s, box-shadow 0.15s;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(244,114,168,0.15) !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.8rem !important;
    color: var(--sk-600) !important;
    font-weight: 500 !important;
    justify-content: center !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.65rem !important;
    color: var(--sk-800) !important;
    font-weight: 700 !important;
}
[data-testid="stMetricDelta"] { justify-content: center !important; }

/* ── DataFrame ── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--sk-100) !important;
    border-radius: 10px !important;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(244,114,168,0.04) !important;
}
[data-testid="stDataFrame"] th {
    background: var(--sk-50) !important;
    color: var(--sk-800) !important;
    font-size: 12px !important;
}

/* ── Plotly 래퍼 ── */
[data-testid="stPlotlyChart"] {
    background: white !important;
    border: 1px solid var(--sk-100) !important;
    border-radius: var(--radius) !important;
    padding: 0.75rem !important;
    box-shadow: var(--shadow-pink) !important;
}

/* ── Alert ── */
[data-testid="stAlert"] { border-radius: 12px !important; }
[data-testid="stAlert"][data-type="info"] {
    background: var(--sk-50) !important;
    border-left: 4px solid var(--sk-400) !important;
}
[data-testid="stAlert"][data-type="info"] p { color: var(--sk-800) !important; }
[data-testid="stAlert"][data-type="success"] {
    background: var(--gn-50) !important;
    border-left: 4px solid var(--gn-400) !important;
}
[data-testid="stAlert"][data-type="success"] p { color: var(--gn-800) !important; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════
# 0. 사이드바 & 데이터 로드
# ══════════════════════════════════════════
if "virtual_today" not in st.session_state:
    st.session_state.virtual_today = datetime.now().date()

with st.sidebar:
    st.markdown("### 📅 시뮬레이션 설정")
    st.date_input("분석 기준일", key="virtual_today")
    virtual_today = datetime.combine(st.session_state.virtual_today, datetime.min.time())
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

total_pool_size = len(sim_df)


# ══════════════════════════════════════════
# 헤더 배너
# ══════════════════════════════════════════
st.markdown(f"""
<div class="page-header">
  <div>
    <div class="page-header-title">📈 마케팅 성과 시뮬레이터</div>
    <div class="page-header-sub">실제 고객 데이터 기반 · 캠페인 전략별 이탈 방어율 비교 분석</div>
  </div>
  <div class="page-header-badge">👥 총 분석 대상 {total_pool_size:,}명</div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════
# 1. 캠페인 그룹 설정
# ══════════════════════════════════════════
st.markdown('<p class="section-title">① 캠페인 그룹 설정</p>', unsafe_allow_html=True)

col_a, col_b = st.columns(2, gap="large")

# ── Group B 먼저 계산 (A 타겟 수가 B에 의존) ──
# B 필터는 col_b 안에서 렌더링되지만 로직은 먼저 처리
_filter_default_idx = 1
_filter_default     = FILTER_OPTIONS_B[_filter_default_idx]
_months_default     = int(_filter_default.split("개월")[0])

# session_state로 B 필터 값 추적
if "filter_b" not in st.session_state:
    st.session_state.filter_b = _filter_default

# B 필터 기준으로 B 타겟 계산
_months_limit  = int(st.session_state.filter_b.split("개월")[0])
target_b_df    = sim_df[sim_df["membership_duration_months"] >= _months_limit]
target_b_count = len(target_b_df)

# A 타겟 수 = 전체 - B 타겟
target_a_count = max(total_pool_size - target_b_count, 0)

# ── Group A 카드 ──
with col_a:
    with st.container():
        st.markdown('<div class="card-pink"></div>', unsafe_allow_html=True) # Anchor
        st.markdown('<span class="card-chip pink">🅰️ GROUP A &nbsp;·&nbsp; 할인 쿠폰</span>', unsafe_allow_html=True)

        # 자동 계산된 타겟 수 표시
        st.markdown(
            f'<div class="target-auto-badge pink">'
            f'<span class="label">🎯 타겟 유저 수 (자동)</span>'
            f'<span class="value">{target_a_count:,}명</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        discount_rate = st.slider("할인율 (%)", 0, 100, 20, step=5, key="d_a",
                                   format="%d%%")
        ret_a, ret_b  = calculate_retention_rates(discount_rate)

        st.markdown(
            f'<div class="rate-badge pink">💡 예상 방어 성공률 &nbsp;<strong>{ret_a*100:.1f}%</strong></div>',
            unsafe_allow_html=True,
        )

# ── Group B 카드 ──
with col_b:
    with st.container():
        st.markdown('<div class="card-green"></div>', unsafe_allow_html=True) # Anchor
        st.markdown('<span class="card-chip green">🅱️ GROUP B &nbsp;·&nbsp; 무료 연장</span>', unsafe_allow_html=True)

        filter_option = st.selectbox(
            "타겟 필터링 조건",
            options=FILTER_OPTIONS_B,
            index=_filter_default_idx,
            key="filter_b",
        )
        # 선택 바뀌면 즉시 반영
        months_limit   = int(filter_option.split("개월")[0])
        target_b_df    = sim_df[sim_df["membership_duration_months"] >= months_limit]
        target_b_count = len(target_b_df)
        target_a_count = max(total_pool_size - target_b_count, 0)

        # 필터링 결과 표시
        st.markdown(
            f'<div class="target-auto-badge green">'
            f'<span class="label">🎯 필터링된 타겟</span>'
            f'<span class="value">{target_b_count:,}명</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<div class="rate-badge green">💡 예상 방어 성공률 &nbsp;<strong>{ret_b*100:.1f}%</strong></div>',
            unsafe_allow_html=True,
        )


# ── rate-badge ↔ expander 사이 여백 ──
st.markdown('<div class="expander-spacer"></div>', unsafe_allow_html=True)

# ── 데이터 미리보기 ──
with st.expander("🔍 시뮬레이션 대상 데이터 미리보기", expanded=False):
    group_view = st.radio(
        "그룹 선택",
        ["할인 쿠폰군 (A)", "무료 연장군 (B)"],
        horizontal=True,
    )
    view_df = (
        sim_df.sort_values("churn_probability", ascending=False).head(target_a_count)
        if group_view == "할인 쿠폰군 (A)" else target_b_df
    )
    display_df = view_df[["user_id", "churn_probability"]].copy()
    display_df["user_id"] = display_df["user_id"].apply(
        lambda x: x[:10] + ".." if isinstance(x, str) else x
    )
    st.dataframe(display_df.head(100), height=230, use_container_width=True)


# ══════════════════════════════════════════
# 2. KPI 요약
# ══════════════════════════════════════════
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown('<p class="section-title">② 성과 예측 요약</p>', unsafe_allow_html=True)

avg_price = sim_df["plan_list_price"].mean() if not sim_df.empty else 149
roi_df, total_rev_a, total_rev_b = calculate_roi_data(
    target_a_count, target_b_count, ret_a, ret_b, discount_rate, avg_price
)
better_group = "A" if total_rev_a > total_rev_b else "B"
diff_rev     = abs(total_rev_a - total_rev_b)

kpi1, kpi2, kpi3 = st.columns(3)
with kpi1:
    st.metric("🌸 Group A 예상 성공률", f"{ret_a*100:.1f}%")
with kpi2:
    st.metric("🌿 Group B 예상 성공률", f"{ret_b*100:.1f}%")
with kpi3:
    st.metric("💰 수익 우위 그룹", f"Group {better_group}", f"+ {diff_rev:,.0f}원")


# ══════════════════════════════════════════
# 3. 수익 차트
# ══════════════════════════════════════════
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown(
    f'<p class="section-title">③ 3개월 누적 수익 추이 &nbsp;'
    f'<span style="font-weight:400;font-size:0.75rem;color:#C94E80">'
    f'{virtual_today.strftime("%Y-%m-%d")} 기준</span></p>',
    unsafe_allow_html=True,
)

fig_rev = px.bar(
    roi_df,
    x="경과 월", y="예상 매출액", color="그룹",
    barmode="group",
    text="예상 매출액",
    color_discrete_map={"할인 쿠폰군 (A)": "#F472A8", "무료 연장군 (B)": "#55A83A"},
)
fig_rev.update_traces(
    texttemplate="%{text:,.0f}",
    textposition="outside",
    marker_line_width=0,
    textfont=dict(size=11, color="#8B2255"),
)
fig_rev.update_layout(
    height=380,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Noto Sans KR", color="#8B2255"),
    title=None,
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02,
        xanchor="right", x=1, title_text="",
        font=dict(size=12),
    ),
    margin=dict(t=40, b=10, l=10, r=10),
    xaxis=dict(title=None, showgrid=False),
    yaxis=dict(title=None, showgrid=True, gridcolor="#F5F0F3", showticklabels=False),
    bargap=0.28,
    bargroupgap=0.08,
)
st.plotly_chart(fig_rev, use_container_width=True)


# ══════════════════════════════════════════
# 4. 종합 결론
# ══════════════════════════════════════════
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown('<p class="section-title">④ 종합 결론</p>', unsafe_allow_html=True)

if better_group == "A":
    st.success(
        f"🟢 **최종 분석**: **할인 쿠폰군(A)**이 캠페인 초기 매출 회수가 빠르며, "
        f"3개월 누적 수익이 무료 연장군(B) 대비 약 **{diff_rev:,.0f}원** 더 높게 예측됩니다.\n\n"
        "👉 **단기 수익 최적화 전략**으로 본 캠페인을 추천합니다."
    )
else:
    st.info(
        f"🔵 **최종 분석**: **무료 연장군(B)**이 첫 달 매출 공백이 있으나, "
        f"고객 유지 효과로 3개월 누적 수익이 할인 쿠폰군(A)보다 약 **{diff_rev:,.0f}원** 더 유리합니다.\n\n"
        "👉 **장기 LTV(고객 생애 가치) 극대화 전략**으로 본 캠페인을 추천합니다."
    )

st.caption(
    f"※ 본 시뮬레이션은 실제 고객 {total_pool_size:,}명을 기반으로 계산되었으며, "
    f"환율 1 TWD = {TWD_TO_KRW}원이 적용되었습니다."
)