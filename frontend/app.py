import streamlit as st

# ==========================================
# 1. 페이지 설정 (공통 레이아웃)
# ==========================================
st.set_page_config(
    page_title="KKBox Churn Defense Portal",
    page_icon="🎵",
    layout="wide"
)

# ==========================================
# 2. 페이지 정의 및 내비게이션 설정
# ==========================================
# 각 기능별 페이지를 정의합니다. (st.Page API 사용)
action_board_page = st.Page(
    "pages/action_board/action_board.py", 
    title="메인 현황판 (Daily Overview)", 
    icon="📊", 
    default=True
)

# 사이드바 내비게이션 그룹화
pg = st.navigation({
    "Dashboard": [action_board_page],
    # 추후 여기에 "이탈 분석", "유저 리스트" 등의 페이지를 추가할 수 있습니다.
})

# ==========================================
# 3. 사이드바 디자인 커스텀
# ==========================================
with st.sidebar:
    st.markdown("---")
    st.caption("🚀 **3팀 프로젝트: 이탈 방어 시스템**")

# 페이지 실행
pg.run()
