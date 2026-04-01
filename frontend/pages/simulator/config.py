# 📈 시뮬레이터 설정 상수

# 그룹별 기본 색상
COLOR_GROUP_A = "#F472A8"  # 할인 쿠폰 (Pink)
COLOR_GROUP_B = "#55A83A"  # 무료 연장 (Green)
COLOR_GRAY = "#E0E0E0"

# ──────────────────────────────────────────
# Group A: 가격 탄력성 기반 방어율 모델
# retention_A(d, p) = 1 - churn_prob * exp(-k * d)
#   d  : 할인율 (0~1)
#   k  : 가격 민감도 계수 (클수록 할인에 민감)
#   결과: 개인별 churn_prob을 할인율로 얼마나 억제하는지 계산
# ──────────────────────────────────────────
A_PRICE_SENSITIVITY_K = 3.5       # 가격 민감도 (실험값: 3~5)
A_MAX_RETENTION_CAP   = 0.85      # 방어율 상한 (아무리 좋아도 85%)

# ──────────────────────────────────────────
# Group B: 가입 기간 가중 방어율 모델
# retention_B(m) = base * (1 + log(1 + m) / loyalty_scale)
#   m            : 가입 기간 (개월)
#   base         : 기본 방어율 (무료 연장에 반응하는 최소 비율)
#   loyalty_scale: 로열티 가중치 스케일
#   결과: 오래된 유저일수록 무료 연장에 더 반응
# ──────────────────────────────────────────
B_BASE_RETENTION      = 0.28      # 기본 방어율 28%
B_LOYALTY_SCALE       = 4.0       # 가입 기간 가중치 분모
B_MAX_RETENTION_CAP   = 0.70      # 방어율 상한 70%

# ──────────────────────────────────────────
# ROI 모델 파라미터
# ──────────────────────────────────────────
# 월별 자연 이탈 감가율: 방어 성공 유저도 매달 일정 비율 재이탈
MONTHLY_CHURN_DECAY   = 0.08      # 매월 8% 추가 이탈

# Group B: 무료 연장 제공 기간 (이 기간 동안 매출 0)
B_FREE_EXTENSION_MONTHS = 1

# 시뮬레이션 기간 (개월)
SIMULATION_MONTHS = 3

# 타겟팅 기본값
DEFAULT_A_TARGET_COUNT = 500
FILTER_OPTIONS_B = ["1개월 이상 가입자", "3개월 이상 가입자", "6개월 이상 가입자"]