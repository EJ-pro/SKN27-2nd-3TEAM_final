"""
app.py — UI 전담 진입점.

책임:
  - Streamlit 레이아웃 구성
  - 사이드바 설정값 수집
  - config / data_layer / metrics 를 조합해 화면에 표시

이 파일은 비즈니스 로직을 직접 구현하지 않습니다.
KPI 계산이 필요하면 metrics.py를 호출하고,
데이터가 필요하면 data_layer.py를 호출합니다.

실행: streamlit run app.py
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from pages.action_board.config import CHURN_REASONS
from pages.action_board.data_layer import inject_churn_probability, load_raw_data
from pages.action_board.metrics import build_kpi_report, build_trend_data, build_churn_reasons

# ── 페이지 설정 ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="KKBox Churn Defense",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.main { background-color: #f5f7f9; }
.stMetric {
    background-color: #ffffff;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
</style>
""", unsafe_allow_html=True)


# ── 데이터 로드 (캐싱) ────────────────────────────────────────────────────────
# @st.cache_resource  → 세션 간 공유가 필요한 무거운 객체 (ML 모델 등)
# @st.cache_data      → 직렬화 가능한 데이터 (DataFrame 등)

@st.cache_resource
def get_model():
    """
    ML 모델 로더. 현재는 None 반환(더미 모드).
    팀원에게 pkl 받으면:
      import joblib
      return joblib.load("models/champion_model.pkl")
    """
    return None


@st.cache_data
def get_transactions() -> "pd.DataFrame":
    raw = load_raw_data()
    model = get_model()
    return inject_churn_probability(raw["transactions"], model=model)


transactions = get_transactions()


# ── 사이드바 ──────────────────────────────────────────────────────────────────
with st.sidebar:

    virtual_today_val = st.date_input(
        "📅 분석 기준일 (Virtual Today)",
        value=datetime.now().date(),
        min_value=datetime(2020, 1, 1).date(),
        max_value=datetime(2030, 12, 31).date(),
    )
    virtual_today = datetime.combine(virtual_today_val, datetime.min.time())


# ── KPI 계산 ──────────────────────────────────────────────────────────────────
report = build_kpi_report(transactions, virtual_today)
trend_df = build_trend_data(transactions, virtual_today)


# ── 헤더 ──────────────────────────────────────────────────────────────────────
st.title("📊 Churn Defense 관제탑")
st.subheader("실시간 이탈 방어 현황 (Data Shifting & Scale-up 적용)")


# ── KPI 카드 ──────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "🚨 실시간 고위험 유저",
        f"{report.today.high_risk_users:,}명",
        f"{report.user_delta:+,}명",
        delta_color="inverse",   # 늘어나면 빨간색 (나쁜 것)
    )

with col2:
    st.metric(
        "💸 매출 위기 총액",
        f"₩{report.today.revenue_at_risk:,.0f}",
        f"₩{report.revenue_delta:+,.0f}",
        delta_color="inverse",   # 늘어나면 빨간색 (나쁜 것)
    )

with col3:
    st.metric(
        "🛡️ 이탈 방어 성공률",
        f"{report.today.defense_rate:.1f}%",
        f"{report.defense_rate_delta:+.1f}%p",
        delta_color="normal",    # 늘어나면 초록색 (좋은 것)
    )

st.divider()


# ── 차트 ──────────────────────────────────────────────────────────────────────
chart_col, pie_col = st.columns(2)

with chart_col:
    st.write("### 📈 최근 7일간 이탈 위험 추이")
    fig_line = px.line(
        trend_df,
        x="날짜",
        y=["고위험 유저", "방어 성공 유저"],
        color_discrete_map={"고위험 유저": "#EF553B", "방어 성공 유저": "#00CC96"},
        markers=True,
        template="plotly_white",
    )
    fig_line.update_layout(
        height=350,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_line, use_container_width=True)

with pie_col:
    st.write("### 🔍 이탈 주원인 분석")
    # TODO: SHAP 변수 중요도 또는 룰베이스 집계 결과로 교체 (config.CHURN_REASONS 수정)
    reason_df = (
        pd.DataFrame(CHURN_REASONS.items(), columns=["원인", "비중"])
    )
    fig_donut = px.pie(
        reason_df,
        values="비중",
        names="원인",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig_donut.update_layout(
        height=400,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig_donut, use_container_width=True)

st.divider()


# ── 운영 요약 ─────────────────────────────────────────────────────────────────
st.write("### 🔔 모니터링 요약")
st.info(f"""
**{virtual_today.strftime('%Y-%m-%d')} 기준 운영 현황**

- 감지된 고위험 유저: **{report.today.high_risk_users:,}명** \
  (전일 대비 {report.user_delta:+,}명)
- 이탈 방어 성공률: **{report.today.defense_rate:.1f}%** \
  (전일 대비 {report.defense_rate_delta:+.1f}%p)
- 주요 알림: 고위험 유저 중 **{max(churn_reasons, key=churn_reasons.get)}** 비중이 가장 높습니다. \
  맞춤형 케어 프로모션 발송을 권장합니다.
""")