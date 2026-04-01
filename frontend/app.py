import streamlit as st

# ==========================================
# 1. 페이지 설정 (공통 레이아웃)
# ==========================================
st.set_page_config(
    page_title="🌸 KKBOX 이탈 방어 시스템",
    page_icon="🌸",
    layout="wide"
)

# ==========================================
# 2. 페이지 정의 및 내비게이션 설정
# ==========================================
# 각 기능별 페이지를 정의합니다. (st.Page API 사용)
action_board_page = st.Page(
    "pages/action_board/action_board.py", 
    title="통합 대시보드", 
    icon="📊", 
    default=True
)

action_manager_page = st.Page(
    "pages/action/app_action.py",
    title="고위험군 액션 보드",
    icon="🎯"
)

app_simulator_page = st.Page(
    "pages/simulator/app_simulator.py",
    title="마케팅 성과 시뮬레이터",
    icon="📈"
)

# 사이드바 내비게이션 그룹화
pg = st.navigation({
    "대시보드": [action_board_page, action_manager_page],
    "시뮬레이터": [app_simulator_page],
})

# 페이지 실행
pg.run()

# ==========================================
# 3. 사이드바 음악 플레이어 (가지마가지마)
# ==========================================
with st.sidebar:
    st.write("🎵 **Now Playing: 벛꽃엔딩**")
    st.components.v1.html(
        """
        <iframe width="100%" height="150" src="https://www.youtube.com/embed/?v=uEsT7K_X7Pw&list=RDuEsT7K_X7Pw&start_radio=1" 
        title="버스커버스커 - 벛꽃엔딩" frameborder="0" 
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
        allowfullscreen></iframe>
        """,
        height=160,
    )
    st.caption("🚀 **3팀 프로젝트: 이탈 방어 시스템**")
