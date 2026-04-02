# 🚀 Project Setup & Execution Guide

본 문서는 프로젝트 클론 후 서비스 실행까지의 전체 파이프라인(환경 설정, 데이터 분석, DB 적재, 서비스 실행)을 안내합니다.

---

## 1. 환경 설정 (Environment Setup)

### 🐍 가상환경 생성 (uv 활용)

프로젝트는 **Python 3.13** 버전을 기반으로 하며, `uv` 도구를 사용하여 가상환경을 구축합니다.

```bash
# 1. 가상환경 생성 (.venv 디렉토리)
uv venv .venv --python 3.13

# 2. 가상환경 활성화 (Windows)
.venv\Scripts\activate

# 3. 필수 라이브러리 설치
uv pip install -r .\requirements.txt
```

### 🔑 환경 변수 설정 (.env)

`backend/.env` 파일을 생성하여 데이터베이스 연결 정보를 설정합니다. (없을 경우 `backend/` 폴더 내에 생성하세요)

```env
DB_HOST=localhost
DB_PORT=3307
DB_NAME=churn_db
DB_USER=root
DB_PASSWORD=app1234
```

---

## 2. 인프라 구축 (Infrastructure)

### 🐳 Docker를 통한 데이터베이스 실행

`backend` 디렉토리에서 Docker Compose를 사용하여 MySQL 서버와 초기 데이터를 셋업합니다.

```bash
cd backend

docker compose down --remove-orphans
docker compose build
docker compose up -d
docker compose exec app bash
python -m scripts.seed_data
```

> [!NOTE]
> DB 포트는 외부 기준 `3307`로 호스팅되어 있습니다.

---

## 3. 데이터 분석 및 모델링 파이프라인 (Data Pipeline)

서비스 구동에 필요한 고위험 유저 예측 및 사유 분석 데이터를 생성합니다. (전체 로그 처리로 인해 시간이 소요될 수 있습니다)

```bash
# 🚀 통합 파이프라인 한 번에 실행 (가장 권장되는 방법)
python model/run_pipeline.py

```

---

## 4. 데이터베이스 및 백엔드 연동 (DB Ingestion)

생성된 분석 결과 CSV 파일을 MySQL DB의 정해진 스키마(`churn_prediction`, `churn_predict_reason` 등)에 안전하게 적재합니다.

```bash
# 분석 결과 DB 적재 실행
python backend/app/ingest/db_ingest.py
```

---

## 5. 서비스 실행 (Frontend)

Streamlit을 통해 대시보드와 마케팅 시뮬레이터 인터페이스를 구동합니다.

```bash
# 프로젝트 루트에서 실행
streamlit run frontend/app.py
```

---

## 💡 파이프라인 요약 순서

1. `uv venv` (가상환경 구성)
2. `backend/.env` (환경 변수 설정)
3. `docker-compose up` (인프라/DB 실행)
4. `python model/run_pipeline.py` (데이터 생성 및 DB 자동 적재)
5. `streamlit run frontend/app.py` (서비스 시작)
