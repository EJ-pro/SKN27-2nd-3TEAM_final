import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta

# [중요] 기존 액션 보드 모듈에서 데이터 처리 로직 재사용
from pages.action_board.config import HIGH_RISK_THRESHOLD, TWD_TO_KRW, EXPIRY_WINDOW_DAYS
from pages.action_board.data_layer import load_raw_data, inject_churn_probability

# ── 페이지 설정 ──
st.title("📈 마케팅 성과 시뮬레이터")
st.caption("실제 고객 데이터를 기반으로 캠페인 전략별 예상 이탈 방어율을 비교 분석합니다.")

# ==========================================
# 0. 데이터 셋업 (Real CSV 기반)
# ==========================================
@st.cache_data
def get_real_sim_data(virtual_today):
    """
    실제 CSV 데이터를 로드하여 분석 기준일 기준의 고위험군 유저 풀을 생성합니다.
    """
    raw_result = load_raw_data()
    if not raw_result or "transactions" not in raw_result:
        st.error("데이터를 불러올 수 없습니다.")
        return pd.DataFrame()
    
    trans_df = raw_result["transactions"]
    prob_df = inject_churn_probability(trans_df)
    
    # 분석 기준일로부터 만료 임박한 유저 필터링
    window_end = virtual_today + timedelta(days=EXPIRY_WINDOW_DAYS)
    mask_date = (prob_df["membership_expire_date"] >= virtual_today) & (prob_df["membership_expire_date"] <= window_end)
    
    # 이탈 확률 0.5 이상의 잠재적 타겟 유저
    candidates = prob_df[mask_date & (prob_df["churn_prob"] >= 0.5)].copy()
    
    # 필드 정리 및 시뮬레이션용 데이터 가공
    # msno -> user_id, churn_prob -> churn_probability
    candidates = candidates.rename(columns={"msno": "user_id", "churn_prob": "churn_probability"})
    
    # 가입 기간 (간이 계산: 오늘 기준 만료일까지 남은 기한 활용 혹은 랜덤 보정)
    rng = np.random.default_rng(42)
    candidates["membership_duration_months"] = rng.integers(1, 13, len(candidates))
    
    return candidates

# 사이드바 설정 (분석 날짜 연동)
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
    # 실제 타겟 풀 내에서 숫자 지정
    target_a_count = st.number_input("타겟 유저 수 (A)", min_value=1, max_value=total_pool_size, value=min(500, total_pool_size), key="n_a")
    discount_rate = st.slider("할인율 (%)", 0, 100, 20, step=5, key="d_a")
    
    # [가설 수식] 할인율이 높을수록 방어율(재가입률) 상승 
    retention_a = (10 + (discount_rate * 0.4)) / 100
    st.info(f"💡 예상 방어 성공률: **{retention_a*100:.1f}%**")

with config_col2:
    st.subheader("🅱️ Group B: 무료 연장")
    # 실제 데이터의 가입 기간 필드를 기반으로 필터링
    filter_option = st.selectbox(
        "타겟 필터링 조건 (B)",
        options=["1개월 이상 가입자", "3개월 이상 가입자", "6개월 이상 가입자"],
        index=1
    )
    
    months_limit = int(filter_option.split("개월")[0])
    target_b_df = sim_df[sim_df["membership_duration_months"] >= months_limit]
    target_b_count = len(target_b_df)
    
    # [가설 수식] 무료 연장의 방어율은 30%로 세팅
    retention_b = 30.0 / 100
    st.write(f"👥 실제 필터링된 타겟: **{target_b_count}명**")
    st.info(f"💡 예상 방어 성공률: **{retention_b*100:.1f}%**")

with config_col3:
    st.subheader("🔍 대상 데이터 조회")
    group_view = st.radio("그룹 선택", ["Group A", "Group B"], horizontal=True)
    
    if group_view == "Group A":
        # A그룹은 이탈 확률 높은 순서대로 타겟팅한다고 가정
        view_df = sim_df.sort_values("churn_probability", ascending=False).head(target_a_count)
    else:
        view_df = target_b_df
        
    # ID 마스킹 처리하여 간략 표출
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
        color_discrete_sequence=[color, "#E0E0E0"],
        title=title
    )
    fig.update_layout(showlegend=False, height=300, margin=dict(t=40, b=0, l=0, r=0))
    return fig

with chart_col1:
    st.plotly_chart(create_donut(retention_a, "Group A 성공률", "#00CC96"), use_container_width=True)

with chart_col2:
    st.plotly_chart(create_donut(retention_b, "Group B 성공률", "#636EFA"), use_container_width=True)

with chart_col3:
    # ROI 수식 구현 (실제 데이터의 평균 플랜 가격 활용)
    avg_price = sim_df["plan_list_price"].mean() if not sim_df.empty else 149
    
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
    
    revenue_data = pd.DataFrame({
        "Month": ["1개월 후", "2개월 후", "3개월 후"] * 2,
        "Group": ["Group A"] * 3 + ["Group B"] * 3,
        "Revenue": rev_a + rev_b
    })
    
    fig_rev = px.bar(
        revenue_data, x="Month", y="Revenue", color="Group",
        barmode="group", title="예상 수익 추이 (원화 환산)",
        color_discrete_map={"Group A": "#00CC96", "Group B": "#636EFA"}
    )
    st.plotly_chart(fig_rev, use_container_width=True)

# ==========================================
# 3. 하단: 시뮬레이션 결론
# ==========================================
st.divider()
total_rev_a = sum(rev_a)
total_rev_b = sum(rev_b)

better_group = "A" if total_rev_a > total_rev_b else "B"
diff_rev = abs(total_rev_a - total_rev_b)

st.write("#### 🛡️ 시뮬레이션 결론")
if better_group == "A":
    st.success(f"🟢 **결론**: Group B(무료 연장)가 초기 방어율은 일정하게 유지되나, **A그룹(할인 쿠폰)이 단기 수익 회수가 빠르고 3개월 누적 수익이 약 {diff_rev:,.0f}원 더 높습니다.**")
else:
    st.info(f"🔵 **결론**: Group A(할인)는 초기 매출 감소가 크지만, **B그룹(무료 연장)이 첫 달 매출 공백을 감수하더라도 고객 유지 효과로 3개월 누적 수익 약 {diff_rev:,.0f}원만큼 더 유리해집니다.**")

st.caption(f"※ 본 시뮬레이션은 실제 고객 {total_pool_size}명을 기반으로 계산되었으며, 환율 1 TWD = {TWD_TO_KRW}원이 적용되었습니다.")
