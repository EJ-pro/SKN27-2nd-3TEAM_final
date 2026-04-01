import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime

# ── 페이지 설정 ──
st.set_page_config(page_title="고위험군 액션 보드 🌸", layout="wide")

# ── 벚꽃 + 초록 봄 테마 CSS ──
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
[data-testid="stSidebar"] * {
    color: var(--sakura-800) !important;
}
[data-testid="stSidebar"] .stDateInput > div > div {
    border-color: var(--sakura-200) !important;
}

/* 메인 타이틀 */
h1 {
    font-size: 2rem !important;
    color: var(--sakura-800) !important;
    border-bottom: 3px solid;
    border-image: linear-gradient(90deg, #FFB3D1, #F472A8, #55A83A, #97D47F) 1;
    padding-bottom: 0.4rem;
}

/* 서브 캡션 */
.stApp [data-testid="stCaptionContainer"] p {
    color: var(--sakura-600) !important;
    font-size: 0.85rem;
}

/* 섹션 헤더 h3 */
h3 {
    color: var(--green-800) !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    margin-top: 0.25rem;
}

/* 구분선 */
hr {
    border: none;
    height: 2px;
    background: linear-gradient(90deg, var(--sakura-200), var(--sakura-400), var(--green-400), var(--green-200));
    margin: 0.75rem 0 1.25rem;
}

/* 멀티셀렉트 */
[data-testid="stMultiSelect"] > div {
    border-color: var(--sakura-200) !important;
    border-radius: 10px !important;
    background: white !important;
}
[data-testid="stMultiSelect"] [data-baseweb="tag"] {
    background-color: var(--sakura-400) !important;
    border-radius: 20px !important;
}
[data-testid="stMultiSelect"] [data-baseweb="tag"] span {
    color: white !important;
}

/* 이탈 원인 멀티셀렉트 — 두 번째 */
div[data-testid="column"]:nth-child(2) [data-testid="stMultiSelect"] > div {
    border-color: var(--green-200) !important;
}
div[data-testid="column"]:nth-child(2) [data-testid="stMultiSelect"] [data-baseweb="tag"] {
    background-color: var(--green-400) !important;
}

/* 탭 */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: transparent !important;
    gap: 4px;
    border-bottom: 2px solid var(--sakura-100);
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    border-radius: 10px 10px 0 0 !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
    padding: 0.6rem 1.5rem !important;
    color: var(--sakura-600) !important;
    border: 1px solid var(--sakura-200) !important;
    border-bottom: none !important;
    background: white !important;
    transition: all 0.15s;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: var(--sakura-400) !important;
    color: white !important;
    border-color: var(--sakura-400) !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
    background: var(--sakura-400) !important;
    height: 0 !important;
}
[data-testid="stTabs"] [data-baseweb="tab-panel"] {
    background: white;
    border: 1px solid var(--sakura-200);
    border-top: none;
    border-radius: 0 0 12px 12px;
    padding: 1rem 1.25rem !important;
}

/* 버튼 기본 */
.stButton > button {
    border-radius: 9px !important;
    font-family: 'Noto Sans KR', sans-serif !important;
    font-weight: 500 !important;
    transition: all 0.15s !important;
    border: 1px solid var(--sakura-200) !important;
    background: white !important;
    color: var(--sakura-800) !important;
}
.stButton > button:hover {
    background: var(--sakura-50) !important;
    border-color: var(--sakura-400) !important;
}

/* primary 버튼 (type="primary") */
.stButton > button[kind="primary"] {
    background: var(--sakura-400) !important;
    border-color: var(--sakura-400) !important;
    color: white !important;
}
.stButton > button[kind="primary"]:hover {
    background: var(--sakura-600) !important;
    border-color: var(--sakura-600) !important;
}

/* 일반탭 primary 버튼은 초록으로 */
#tab-general .stButton > button[kind="primary"] {
    background: var(--green-400) !important;
    border-color: var(--green-400) !important;
}
#tab-general .stButton > button[kind="primary"]:hover {
    background: var(--green-600) !important;
}

/* 데이터 에디터 */
[data-testid="stDataEditor"] {
    border: 1px solid var(--sakura-100) !important;
    border-radius: 10px !important;
    overflow: hidden;
}
[data-testid="stDataEditor"] th {
    background: var(--sakura-50) !important;
    color: var(--sakura-800) !important;
    font-weight: 600;
}
[data-testid="stDataEditor"] tr:hover td {
    background: var(--sakura-50) !important;
}

/* success / info / warning 메시지 */
[data-testid="stAlert"][data-type="success"] {
    background: var(--green-50) !important;
    border-left: 4px solid var(--green-400) !important;
    border-radius: 10px !important;
    color: var(--green-800) !important;
}
[data-testid="stAlert"][data-type="info"] {
    background: var(--sakura-50) !important;
    border-left: 4px solid var(--sakura-400) !important;
    border-radius: 10px !important;
    color: var(--sakura-800) !important;
}
[data-testid="stAlert"][data-type="warning"] {
    border-radius: 10px !important;
}

/* 스피너 */
[data-testid="stSpinner"] {
    color: var(--sakura-400) !important;
}

/* date_input */
[data-testid="stDateInput"] input {
    border-color: var(--sakura-200) !important;
    border-radius: 9px !important;
    background: var(--sakura-50) !important;
}
[data-testid="stDateInput"] input:focus {
    border-color: var(--sakura-400) !important;
    box-shadow: 0 0 0 3px rgba(244,114,168,0.15) !important;
}
/* --- 벚꽃 낙하 애니메이션 (추가) --- */
.petal {
    position: fixed;
    top: -10%;
    z-index: 9999;
    pointer-events: none;
    background: #FFB3D1; /* --sakura-200 */
    border-radius: 150% 0 150% 0;
    opacity: 0.6;
    transform-origin: left top;
    animation: sakura-fall linear forwards;
}

@keyframes sakura-fall {
    0% {
        transform: translateY(0) rotate(0deg) translateX(0);
        opacity: 0.8;
    }
    100% {
        transform: translateY(110vh) rotate(720deg) translateX(100px);
        opacity: 0;
    }
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# [모듈화] 전용 설정 및 데이터 레이어 임포트
# ==========================================
# 아래 import는 실제 모듈 파일이 있을 때 활성화하세요
# from pages.action.config import (
#     PLUS_PRICE_THRESHOLD, RISK_GRADES, VVIP_ACTION_TEXT,
#     GENERAL_ACTION_TEXT, VVIP_SUCCESS_MSG, GENERAL_SUCCESS_MSG
# )
# from pages.action_board.config import CHURN_REASONS
# from pages.action.data_layer import get_real_action_data, apply_filters, segment_by_plus_price

# ── 임시 상수 (config 모듈 연동 전 fallback) ──
PLUS_PRICE_THRESHOLD = 50000
RISK_GRADES          = ["HIGH", "MID", "LOW"]
VVIP_ACTION_TEXT     = "💎 프리미엄 리텐션 쿠폰 발송"
GENERAL_ACTION_TEXT  = "🌱 재참여 유도 메시지 발송"
VVIP_SUCCESS_MSG     = "💎 {}명에게 프리미엄 리텐션 쿠폰이 발송되었습니다!"
GENERAL_SUCCESS_MSG  = "🌱 {}명에게 재참여 유도 메시지가 발송되었습니다!"
CHURN_REASONS        = {
    "가격": "가격 불만족",
    "기능": "기능 부족",
    "경쟁사": "경쟁사 이탈",
    "서비스": "서비스 불만",
}

# ── 임시 데이터 함수 (data_layer 모듈 연동 전 fallback) ──
def get_real_action_data(virtual_today: pd.Timestamp) -> pd.DataFrame:
    """실제 데이터 레이어 연동 전 샘플 데이터를 반환합니다."""
    return pd.DataFrame([
        {"user_id": "user_a1b2c3d4e5", "churn_probability": 0.87, "plus_price": 128000,
         "risk_grade": "HIGH", "churn_reason": "가격",   "membership_expire_date": pd.Timestamp("2025-04-15")},
        {"user_id": "user_c3d4e5f6g7", "churn_probability": 0.72, "plus_price": 95000,
         "risk_grade": "HIGH", "churn_reason": "경쟁사", "membership_expire_date": pd.Timestamp("2025-04-18")},
        {"user_id": "user_e5f6g7h8i9", "churn_probability": 0.65, "plus_price": 210000,
         "risk_grade": "MID",  "churn_reason": "기능",   "membership_expire_date": pd.Timestamp("2025-04-22")},
        {"user_id": "user_g7h8i9j0k1", "churn_probability": 0.58, "plus_price": 180000,
         "risk_grade": "MID",  "churn_reason": "서비스", "membership_expire_date": pd.Timestamp("2025-04-30")},
        {"user_id": "user_i9j0k1l2m3", "churn_probability": 0.90, "plus_price": 32000,
         "risk_grade": "HIGH", "churn_reason": "가격",   "membership_expire_date": pd.Timestamp("2025-04-12")},
        {"user_id": "user_k1l2m3n4o5", "churn_probability": 0.79, "plus_price": 18000,
         "risk_grade": "HIGH", "churn_reason": "기능",   "membership_expire_date": pd.Timestamp("2025-04-16")},
        {"user_id": "user_m3n4o5p6q7", "churn_probability": 0.63, "plus_price": 27000,
         "risk_grade": "MID",  "churn_reason": "경쟁사", "membership_expire_date": pd.Timestamp("2025-04-20")},
        {"user_id": "user_o5p6q7r8s9", "churn_probability": 0.55, "plus_price": 41000,
         "risk_grade": "MID",  "churn_reason": "서비스", "membership_expire_date": pd.Timestamp("2025-04-25")},
        {"user_id": "user_q7r8s9t0u1", "churn_probability": 0.48, "plus_price": 15000,
         "risk_grade": "LOW",  "churn_reason": "가격",   "membership_expire_date": pd.Timestamp("2025-05-01")},
    ])

def apply_filters(df: pd.DataFrame, grades: list, reasons: list) -> pd.DataFrame:
    return df[df["risk_grade"].isin(grades) & df["churn_reason"].isin(reasons)]

def segment_by_plus_price(df: pd.DataFrame, threshold: int):
    return df[df["plus_price"] >= threshold].copy(), df[df["plus_price"] < threshold].copy()


def trigger_cherry_blossoms():
    """화면에 벚꽃이 떨어지는 효과를 확실하게 트리거합니다."""
    import time
    timestamp = time.time()
    sakura_js = f"""
    <div id="sakura-trigger-{timestamp}"></div>
    <script>
    (function() {{
        const parentDoc = window.parent.document;
        
        // 기존 컨테이너가 있으면 제거 (동시 실행 방지)
        const oldContainer = parentDoc.getElementById('sakura-container');
        if (oldContainer) oldContainer.remove();

        const container = parentDoc.createElement('div');
        container.id = 'sakura-container';
        container.style.position = 'fixed';
        container.style.top = '0';
        container.style.left = '0';
        container.style.width = '100vw';
        container.style.height = '100vh';
        container.style.pointerEvents = 'none';
        container.style.zIndex = '99999';
        parentDoc.body.appendChild(container);

        function createPetal() {{
            const petal = parentDoc.createElement('div');
            petal.style.position = 'absolute';
            petal.style.top = '-20px';
            petal.style.left = Math.random() * 100 + 'vw';
            const size = Math.random() * 15 + 10;
            petal.style.width = size + 'px';
            petal.style.height = size + 'px';
            petal.style.backgroundColor = ['#FFB3D1', '#FFD6E7', '#F472A8'][Math.floor(Math.random() * 3)];
            petal.style.borderRadius = '150% 0 150% 0';
            petal.style.opacity = '0.8';
            petal.style.transformOrigin = 'left top';
            
            const duration = Math.random() * 3 + 3;
            petal.animate([
                {{ transform: 'translateY(0) rotate(0deg) translateX(0)', opacity: 0.8 }},
                {{ transform: `translateY(110vh) rotate(${{Math.random() * 720}}deg) translateX(${{Math.random() * 150}}px)`, opacity: 0 }}
            ], {{
                duration: duration * 1000,
                easing: 'linear',
                fill: 'forwards'
            }});

            container.appendChild(petal);
            setTimeout(() => petal.remove(), duration * 1000);
        }}

        // 벚꽃 생성 (꽃가루 느낌으로 충분히 많이)
        for (let i = 0; i < 70; i++) {{
            setTimeout(createPetal, i * 70);
        }}
        
        // 10초 후 컨테이너 완전 제거
        setTimeout(() => {{
            if (container.parentNode) container.remove();
        }}, 10000);
    }})();
    </script>
    """
    components.html(sakura_js, height=0)


# ==========================================
# 세션 상태 초기화
# ==========================================
if "vvip_selected" not in st.session_state:
    st.session_state.vvip_selected = False
if "general_selected" not in st.session_state:
    st.session_state.general_selected = False


# ==========================================
# 페이지 타이틀
# ==========================================
st.markdown("🌸 &nbsp; **봄**", unsafe_allow_html=True)   # 작은 데코
st.title("고위험군 액션 보드")
st.caption("고객 가치에 따라 그룹을 나누어 맞춤형 마케팅 액션을 시뮬레이션합니다.")
st.markdown("<hr>", unsafe_allow_html=True)


# ==========================================
# 1. 사이드바 — 분석 기준일
# ==========================================
with st.sidebar:
    st.markdown("### 📅 시뮬레이션 설정")
    virtual_today_val = st.date_input("분석 기준일", value=datetime.now().date())
    virtual_today     = pd.to_datetime(virtual_today_val)

    st.markdown("---")
    st.markdown(
        "<small style='color:#C94E80'>🌸 봄 시즌 리텐션 캠페인</small>",
        unsafe_allow_html=True
    )


# ==========================================
# 2. 데이터 로드
# ==========================================
with st.spinner("🌸 데이터 분석 중..."):
    target_df = get_real_action_data(virtual_today)

if target_df.empty:
    st.warning("분석일 기준 만료 예정인 고위험 유저가 없습니다.")
    st.stop()


# ==========================================
# 3. 공통 필터
# ==========================================
st.markdown("### ⚙️ 공통 필터")

f_col1, f_col2 = st.columns(2)

with f_col1:
    selected_grades = st.multiselect(
        "위험 등급",
        options=RISK_GRADES,
        default=RISK_GRADES,
        key="selected_grades_filter",
    )

with f_col2:
    all_reasons     = list(CHURN_REASONS.keys())
    selected_reasons = st.multiselect(
        "이탈 원인",
        options=all_reasons,
        default=all_reasons,
        key="selected_reasons_filter",
    )

filtered_df = apply_filters(target_df, selected_grades, selected_reasons)

st.markdown("<hr>", unsafe_allow_html=True)


# ==========================================
# 4. plus_price 기반 그룹 분리
# ==========================================
vvip_df, general_df = segment_by_plus_price(filtered_df, PLUS_PRICE_THRESHOLD)

tab_vvip, tab_general = st.tabs([
    f"💎 우량 고객 ({len(vvip_df)}명)",
    f"🌱 일반/신규 고객 ({len(general_df)}명)",
])


# ──────────────────────────────────────────
# 탭 1 : 💎 우량 고객 (VVIP)
# ──────────────────────────────────────────
with tab_vvip:
    if len(vvip_df) > 0:
        c1, c2, _ = st.columns([1, 1, 5])
        if c1.button("✅ 전체 선택", key="btn_vvip_all"):
            st.session_state.vvip_selected = True
            st.rerun()
        if c2.button("⭕ 선택 해제", key="btn_vvip_none"):
            st.session_state.vvip_selected = False
            st.rerun()

        vvip_df["[☑️ 타겟 선택]"] = st.session_state.vvip_selected

        # ID 마스킹
        vvip_display = vvip_df.copy()
        vvip_display["user_id"] = vvip_display["user_id"].apply(
            lambda x: x[:10] + ".." if isinstance(x, str) else x
        )

        vvip_edit = st.data_editor(
            vvip_display,
            hide_index=True,
            key="editor_vvip",
            use_container_width=True,
            column_config={
                "churn_probability": st.column_config.ProgressColumn(
                    "이탈 확률", format="%.2f", min_value=0, max_value=1
                ),
                "plus_price": st.column_config.NumberColumn(
                    "기대 추가 수익", format="₩%d"
                ),
                "membership_expire_date": st.column_config.DateColumn("만료일"),
            },
        )

        v_sel = vvip_edit[vvip_edit["[☑️ 타겟 선택]"] == True]
        if len(v_sel) > 0:
            st.markdown(
                f"<small style='color:#C94E80'>✔ {len(v_sel)}명 선택됨</small>",
                unsafe_allow_html=True,
            )
            if st.button(VVIP_ACTION_TEXT, type="primary", key="act_vvip"):
                trigger_cherry_blossoms()
                st.success(VVIP_SUCCESS_MSG.format(len(v_sel)))
    else:
        st.info("조건에 맞는 우량 고객이 없습니다.")


# ──────────────────────────────────────────
# 탭 2 : 🌱 일반/신규 고객 (General)
# ──────────────────────────────────────────
with tab_general:
    if len(general_df) > 0:
        c1, c2, _ = st.columns([1, 1, 5])
        if c1.button("✅ 전체 선택", key="btn_gen_all"):
            st.session_state.general_selected = True
            st.rerun()
        if c2.button("⭕ 선택 해제", key="btn_gen_none"):
            st.session_state.general_selected = False
            st.rerun()

        general_df["[☑️ 타겟 선택]"] = st.session_state.general_selected

        gen_display = general_df.copy()
        gen_display["user_id"] = gen_display["user_id"].apply(
            lambda x: x[:10] + ".." if isinstance(x, str) else x
        )

        gen_edit = st.data_editor(
            gen_display,
            hide_index=True,
            key="editor_gen",
            use_container_width=True,
            column_config={
                "churn_probability": st.column_config.ProgressColumn(
                    "이탈 확률", format="%.2f", min_value=0, max_value=1
                ),
                "plus_price": st.column_config.NumberColumn(
                    "기대 추가수익", format="₩%d"
                ),
                "membership_expire_date": st.column_config.DateColumn("만료일"),
            },
        )

        g_sel = gen_edit[gen_edit["[☑️ 타겟 선택]"] == True]
        if len(g_sel) > 0:
            st.markdown(
                f"<small style='color:#2E7D1A'>✔ {len(g_sel)}명 선택됨</small>",
                unsafe_allow_html=True,
            )
            if st.button(GENERAL_ACTION_TEXT, type="primary", key="act_gen"):
                trigger_cherry_blossoms()
                st.success(GENERAL_SUCCESS_MSG.format(len(g_sel)))
    else:
        st.info("조건에 맞는 일반 고객이 없습니다.")