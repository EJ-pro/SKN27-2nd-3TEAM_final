import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# ── 페이지 설정 ──
st.title("📈 마케팅 성과 시뮬레이터 (A/B Test)")
st.caption("캠페인 전략별 예상 이탈 방어율과 ROI(수익성)를 실시간으로 비교 분석합니다.")

# ==========================================
# 0. 데모 데이터 셋업 (시뮬레이션용)
# ==========================================
@st.cache_data
def get_sim_data():
    """
    1000명 규모의 가상 고객 데이터를 생성합니다.
    """
    rng = np.random.default_rng(42)
    n = 1000
    df = pd.DataFrame({
        "user_id": [f"user_{rng.integers(100000, 999999)}_{i}" for i in range(n)],
        "churn_probability": rng.uniform(0.5, 1.0, n),
        "membership_duration_months": rng.integers(1, 13, n),
        "plan_list_price": 149  # KKBox의 일반적인 플랜 가격
    })
    return df

sim_df = get_sim_data()

# ==========================================
# 1. 상단: 캠페인 그룹 설정
# ==========================================
st.divider()
config_col1, config_col2, config_col3 = st.columns([2, 2, 1.5], gap="large")

with config_col1:
    st.subheader("🅰️ Group A: 할인 쿠폰")
    # 타겟 수와 할인율 입력
    target_a_count = st.number_input("타겟 유저 수 (A)", min_value=1, max_value=1000, value=500, key="n_a")
    discount_rate = st.slider("할인율 (%)", 0, 100, 20, step=5, key="d_a")
    
    # [가상 수식] 할인율이 높을수록 방어율(재가입률) 상승 
    # 기본 10% + (할인율의 40%만큼 추가 상승)
    retention_a = (10 + (discount_rate * 0.4)) / 100
    st.info(f"💡 예상 방어 성공률: **{retention_a*100:.1f}%**")

with config_col2:
    st.subheader("🅱️ Group B: 무료 연장")
    # 특정 조건으로 필터링하여 타겟 자동 설정
    filter_option = st.selectbox(
        "타겟 필터링 조건 (B)",
        options=["2개월 이상 가입자", "3개월 이상 가입자", "6개월 이상 가입자"],
        index=1
    )
    
    # 필터 조건에 맞는 유저 수 계산
    months_limit = int(filter_option.split("개월")[0])
    target_b_df = sim_df[sim_df["membership_duration_months"] >= months_limit]
    target_b_count = len(target_b_df)
    
    # [가상 수식] 무료 연장의 방어율은 30%로 고정 (또는 보수적 세팅)
    retention_b = 30.0 / 100
    st.write(f"👥 필터링된 타겟: **{target_b_count}명**")
    st.info(f"💡 예상 방어 성공률: **{retention_b*100:.1f}%**")

with config_col3:
    st.subheader("🔍 대상 데이터 조회")
    group_view = st.radio("그룹 선택", ["Group A", "Group B"], horizontal=True)
    
    if group_view == "Group A":
        # A그룹은 상위 N명 추출
        view_df = sim_df.sort_values("churn_probability", ascending=False).head(target_a_count)
    else:
        view_df = target_b_df
        
    # ID 마스킹 처리하여 간략 표출
    display_df = view_df[["user_id", "churn_probability"]].copy()
    display_df["user_id"] = display_df["user_id"].apply(lambda x: x[:10] + "..")
    st.dataframe(display_df.head(100), height=200, use_container_width=True)

# ==========================================
# 2. 중단: 시뮬레이션 결과 차트
# ==========================================
st.divider()
st.write("### 📊 캠페인 성과 예측 결과 (3개월 시뮬레이션)")
chart_col1, chart_col2, chart_col3 = st.columns([1, 1, 2])

# Donut Chart 생성 함수
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
    # ROI 수식 구현 (3개월 추이)
    # A: 결제 직후 수익 발생 (할인가 적용)
    # B: 첫 달은 0원 (무료 연장이니까), 2~3개월차는 정가 결제
    
    unit_price = 149
    
    # 월별 수익 리스트
    rev_a = [
        (target_a_count * retention_a) * (unit_price * (1 - discount_rate/100)), # 1월
        (target_a_count * retention_a) * unit_price,                            # 2월 (유지 시 정가)
        (target_a_count * retention_a) * unit_price                             # 3월
    ]
    
    rev_b = [
        (target_b_count * retention_b) * 0,                                     # 1월 (무료)
        (target_b_count * retention_b) * unit_price,                            # 2월
        (target_b_count * retention_b) * unit_price                             # 3월
    ]
    
    revenue_data = pd.DataFrame({
        "Month": ["1개월 후", "2개월 후", "3개월 후"] * 2,
        "Group": ["Group A"] * 3 + ["Group B"] * 3,
        "Revenue": rev_a + rev_b
    })
    
    fig_rev = px.bar(
        revenue_data, x="Month", y="Revenue", color="Group",
        barmode="group", title="예상 수익 추이 (TWD)",
        color_discrete_map={"Group A": "#00CC96", "Group B": "#636EFA"}
    )
    st.plotly_chart(fig_rev, use_container_width=True)

# ==========================================
# 3. 하단: 시스템 자동 결론 도출 (AI Recommendation)
# ==========================================
st.divider()
total_rev_a = sum(rev_a)
total_rev_b = sum(rev_b)

better_group = "A" if total_rev_a > total_rev_b else "B"
diff_rev = abs(total_rev_a - total_rev_b)

"""
🚨 [TODO 주석: Groq API 연동 구역] 🚨
여기에 Groq API를 연결하여 동적인 추천 메시지를 받아오세요.

```python
def get_groq_recommendation(group_a_rev, group_b_rev, retention_a, retention_b):
    # TODO: Groq API를 호출하여 프롬프트를 던지고 분석 답변을 받아오세요.
    # prompt = f\"\"\"
    # Group A(할인)의 3개월 예상수익은 {group_a_rev}원, 방어율은 {retention_a}%입니다.
    # Group B(무료연장)의 3개월 예상수익은 {group_b_rev}원, 방어율은 {retention_b}%입니다.
    # 어떤 전략이 장기적으로 유리할지 1문장으로 요약해줘.
    # \"\"\"
    return "AI 추천을 서버에서 불러오는 중..."
```
"""

st.write("#### 🛡️ AI 전략 제언 (시뮬레이션 결론)")
if better_group == "A":
    st.success(f"🟢 **결론**: Group B(무료 연장)가 초기 방어율은 일정하게 유지되나, **A그룹(할인 쿠폰)이 단기 수익 회수가 빠르고 3개월 누적 수익이 {diff_rev:,.0f} TWD 더 높습니다.** 장기 ROI 측면에서 A그룹 전략을 추천합니다.")
else:
    st.info(f"🔵 **결론**: Group A(할인)는 초기 매출 감소가 크지만, **B그룹(무료 연장)이 첫 달 매출 공백을 감수하더라도 고객 락인(Lock-in) 효과로 3개월 누적 수익 {diff_rev:,.0f} TWD만큼 더 전세를 뒤바꿉니다.**")

st.caption("※ 본 시뮬레이션은 가상의 재가입률 함수를 기반으로 하였으며, 실제 마케팅 집행 시 결과가 달라질 수 있습니다.")
