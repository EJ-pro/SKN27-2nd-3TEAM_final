# 📈 시뮬레이터 설정 상수

# 그룹별 기본 색상
COLOR_GROUP_A = "#00CC96"  # 할인 쿠폰 (Green)
COLOR_GROUP_B = "#636EFA"  # 무료 연장 (Blue)
COLOR_GRAY = "#E0E0E0"

# 캠페인 가설 수식 상수
# Group A: 할인율에 따른 방어율 (10% + 할인율 * 0.4)
A_BASE_RETENTION = 10.0
A_RETENTION_FACTOR = 0.4

# Group B: 무료 연장 고정 방어율
B_FIXED_RETENTION = 30.0

# 타겟팅 기본값
DEFAULT_A_TARGET_COUNT = 500
FILTER_OPTIONS_B = ["1개월 이상 가입자", "3개월 이상 가입자", "6개월 이상 가입자"]

# ROI 시뮬레이션 기간 (개월)
SIMULATION_MONTHS = 3
