# 🌸 KKBox 이탈율 예측 및 마케팅 시뮬레이터

## 📌 1. 프로젝트 개요 
- **프로젝트 명**: KKBox 데이터셋 기반 고객 이탈 예측 및 마케팅 시뮬레이터 서비스
- **목표**: 머신러닝 모델로 고객 이탈을 정밀하게 예측하고, 예측 결과 및 이탈 기여 원인을 데이터베이스에 적재하여, 마케터가 직관적으로 볼 수 있는 **시각화 대시보드** 및 **캠페인 ROI 시뮬레이터**를 제공함.
- **주요 서비스 흐름**:
  ```mermaid
  graph TD
      A[KKBox Raw Data] --> B[final_model.py: XGBoost 5-Fold Stratified CV]
      B --> C[analysis_model.py: SHAP Contrib 이탈 사유 추출]
      C --> D[user_future.py: Winback 예측 및 감가 계산]
      D --> E[db_ingest.py: MySQL DB 적재]
      E --> F[Streamlit Dashboard / React + FastAPI]
  ```

---

## 2. 나의 역할 및 기여

프로젝트의 **PM 겸 풀스택 ML 엔지니어**로서 머신러닝 파이프라인 설계, 데이터 엔지니어링(DB 적재 및 스키마), 프론트엔드 시각화 및 시뮬레이터 수식화, 배포 최적화 등 프로젝트 전반의 기술적 뼈대와 실질적인 비즈니스 로직을 주도적으로 구현했습니다.

| 대분류 | 상세 기여 내용 | 관련 코드 / 파일 |
| :--- | :--- | :--- |
| **기획 및 아키텍처** | - 가상환경(`uv`) 빌드 및 의존성 구성 관리<br>- Streamlit 폴더 구조 수립 및 모듈화 기획<br>- 요구사항정의서 및 ERD 설계 작성 | - `requirements.txt`<br>- `Doc/wbs.md`<br>- `frontend/pages/` |
| **머신러닝 & 파이프라인** | - XGBoost 기반 5-Fold Stratified Cross Validation 앙상블 모델 개발<br>- SHAP 기여도(`pred_contribs`) 기반 개별 유저 이탈 사유 및 위험 등급 산출<br>- 모델 예측-분석-시뮬레이션-DB 적재까지의 **원클릭 통합 파이프라인** 설계 | - `model/final_model.py`<br>- `model/analysis_model.py`<br>- `model/run_pipeline.py` |
| **데이터 엔지니어링** | - MySQL DB 스키마 설계 및 Docker Compose 컨테이너 인프라 세팅<br>- 중복 제거 및 분석 완료 데이터의 트랜잭션 안전 적재(delete-and-insert) 스크립트 작성 | - `backend/docker-compose.yml`<br>- `backend/docker/mysql/init/01_schema.sql`<br>- `backend/app/ingest/db_ingest.py` |
| **프론트엔드 (Streamlit)** | - 대시보드(Action Board) 데이터 연동 및 Plotly 차트 시각화<br>- **마케팅 성과 시뮬레이터(Simulator)**의 핵심 수학적 모델 수식 적용 및 UI 개발 | - `frontend/pages/simulator/`<br>- `frontend/pages/action_board/` |
| **백엔드 & 배포 (FastAPI/React)** | - FastAPI 백엔드 및 React/TypeScript 프론트엔드 포팅 및 API 연동<br>- Vercel 클라우드 배포를 위한 Monorepo 빌드 설정 및 의존성 최적화 | - `backend/main.py`<br>- `frontend-vite/src/App.tsx`<br>- `vercel.json` |

---

## 3. 핵심 구현 디테일

### 3.1. SHAP 스타일의 이탈 요인 분석 엔진 (`model/analysis_model.py`)
단순히 "이탈할 것이다"라는 확률 제공을 넘어, 마케터가 액션을 취할 수 있도록 개별 고객별 이탈의 핵심 원인을 제공합니다.
- **구현 방식**: 앙상블된 XGBoost 모델 각각에서 `pred_contribs=True` 옵션을 이용해 개별 Feature의 SHAP 스타일 기여도를 추출하고, 이를 평균 내어 기여도가 높은 상위 3가지 요인을 실시간 추출합니다.
- **비즈니스 매핑**: 영어 피처명을 직관적인 한글 사유 및 카테고리로 변환했습니다.
  - `is_auto_renew` ➡️ **"자동결제 미설정"** (카테고리: 결제 및 구독)
  - `total_secs` ➡️ **"재생 시간 부족"** (카테고리: 활동 및 참여)
  - `unique_ratio` ➡️ **"청취 다양성 부족"** (카테고리: 콘텐츠 이용 습관)

### 3.2. 수학적 마케팅 시뮬레이터 모델 (`frontend/pages/simulator/`)
마케팅 캠페인의 유형별로 다르게 작용하는 고객 방어 메커니즘을 수학적으로 모델링하여 ROI를 계산합니다.
- **Group A (할인 쿠폰형) - 가격 탄력성 지수 모델**:
  $$\text{Retention Rate} = 1 - \text{Churn Prob} \times e^{-k \times d}$$
  *(여기서 $d$는 할인율, $k$는 가격 민감도 계수. 할인이 높을수록 이탈률이 기하급수적으로 감소)*
- **Group B (무료 연장형) - 가입 기간 로열티 모델**:
  $$\text{Retention Rate} = \text{Base Retention} \times \left(1 + \frac{\ln(1 + m)}{\text{Loyalty Scale}}\right)$$
  *(여기서 $m$은 가입 개월 수. 가입 기간이 길어 브랜드 신뢰가 있는 고객일수록 무료 연장 캠페인에 더 크게 반응함)*
  - **3개월 누적 ROI 예측**: 매월 일정한 이탈 감가(`MONTHLY_CHURN_DECAY`)를 적용한 후, 첫 달 매출 공백(무료 연장)과 장기 잔존율 추이를 시뮬레이션하여 최종 우위 그룹을 동적으로 제안합니다.

---

## 4. 위기 극복 및 문제 해결 과정

### 1. 대용량 KKBox 데이터로 인한 로컬 메모리 부족 및 Git 파일 제한 문제
- **상황**: 원본 KKBox 데이터셋(Members, Transactions, User Logs)이 수 기가바이트(GB)에 달해 로컬 메모리에서 전처리 중 OOM(Out Of Memory)이 발생하고, 대용량 파일이 실수로 GitHub 리포지토리에 올라가 Push가 막히는 문제 발생.
- **해결책**:
  - `pandas` 로드 시 데이터 중복 제거(`drop_duplicates`)를 가장 먼저 실행하고 필수적인 컬럼만 피처 엔지니어링하여 메모리 점유율을 **80% 이상 절감**.
  - Docker Compose를 구축하여 MySQL 데이터베이스 서버를 로컬 컨테이너로 띄우고 볼륨 마운트 처리. 원본 데이터는 DB 내에 격리하고 분석 결과만 CSV로 남기도록 파이프라인 분리.
  - `.gitignore` 설정을 강화하여 대용량 CSV가 커밋되지 않도록 통제.

### 2. 머신러닝 예측 결과의 비즈니스적 설명력(Explainability) 한계
- **상황**: XGBoost 앙상블 모델은 우수한 성능(AUC 0.90+)을 보였으나, 마케팅 부서에서는 특정 유저가 "왜 이탈 고위험군인지" 알 수 없어 구체적인 방어 캠페인 수립이 어렵다는 피드백 접수.
- **해결책**:
  - `model/analysis_model.py`를 새로 구현하여 XGBoost 모델의 트리 예측 경로에서 계산되는 **SHAP 기반 Feature Contribution**(`pred_contribs`)을 수집하는 엔진 구축.
  - 각 유저별로 이탈 기여도가 가장 큰 변수 3개를 추출하고, 이를 비즈니스 카테고리(구독결제, 서비스 이용, 이용습관 등)와 한글 이탈 사유(예: "완청 횟수 부족", "자동결제 미설정")로 자동 매핑해 주는 테이블 레이어를 구축하여 DB 적재 성공.

### 3. 마케팅 성과 시뮬레이터의 신뢰도 저하 (더미 통계치 한계)
- **상황**: 초기에 제작한 시뮬레이터는 할인율 슬라이더를 움직여도 미리 정해진 단순 평균값만 곱해 수익을 보여주었기에, 실제 마케팅 전략 수립에 활용하기엔 현실성이 크게 떨어짐.
- **해결책**:
  - 미시경제학 및 마케팅 이론을 참고하여 **가격 탄력성 지수 모델(Group A)**과 **로열티 가중 모델(Group B)**을 실시간 연동하는 알고리즘 설계.
  - Streamlit의 `st.cache_data`를 활용해 DB에서 로드된 실제 고객 cohort 풀을 메모리에 올리고, 슬라이더 변경 시 각 개인의 실제 이탈 확률과 가입 기간을 대입하여 **실시간 3개월 시각 시뮬레이션(Plotly)**이 유기적으로 반응하도록 코드 전면 리팩토링.

### 4. Vercel 배포 시 Python 라이브러리 용량 제한 및 빌드 타임아웃 오류
- **상황**: FastAPI 백엔드 및 React 프론트엔드를 클라우드에 배포하려 했으나, AI 모델 학습에 사용된 무거운 패키지들(XGBoost, CatBoost, Scikit-learn, Plotly 등)이 `requirements.txt`에 포함되어 Vercel Serverless Function 250MB 제한을 초과하고 빌드가 타임아웃됨.
- **해결책**:
  - 백엔드 의존성 파일인 `requirements.txt`와 전체 개발용 패키지 `requirements-all.txt`를 분리.
  - Vercel API 실행에 필요한 경량 라이브러리(FastAPI, SQLAlchemy, PyMySQL, Pandas)만 `requirements.txt`에 남기고, 무거운 모델 학습 패키지는 제외함.
  - Vercel 배포용 `vercel.json` 설정 파일 및 React의 빌드 설정을 수정하여, 정적 분석용 더미 데이터를 fallback 처리하는 로직을 FastAPI에 구현함으로써 배포 성공.

---

## 🛠️ 5. 프로젝트 빌드 및 실행 가이드 (Setup Guide)

<details>
<summary>▶️ 로컬 개발 환경 실행 방법 펼치기</summary>

### 5.1. 가상환경 생성 (uv 활용)
프로젝트는 **Python 3.13** 버전을 기반으로 하며, `uv` 도구를 사용하여 가상환경을 구축합니다.
```bash
uv venv .venv --python 3.13
.venv\Scripts\activate
uv pip install -r .\requirements.txt
```

### 5.2. 환경 변수 설정 (.env)
`backend/.env` 파일을 생성하여 데이터베이스 연결 정보를 설정합니다.
```env
DB_HOST=localhost
DB_PORT=3307
DB_NAME=churn_db
DB_USER=root
DB_PASSWORD=app1234
```

### 5.3. Docker DB 인프라 실행
```bash
cd backend
docker compose down --remove-orphans
docker compose build
docker compose up -d
docker compose exec app bash
python -m scripts.seed_data
```

### 5.4. 데이터 파이프라인 (예측/분석/DB 적재) 원클릭 구동
```bash
python model/run_pipeline.py
```

### 5.5. Streamlit 서비스 시작
```bash
streamlit run frontend/app.py
```
</details>
