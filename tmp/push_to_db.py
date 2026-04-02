
import os
import pandas as pd
from sqlalchemy import create_engine

# 1. 환경 설정 (data_layer.py와 동일)
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root1234")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3307")
DB_NAME = os.getenv("DB_NAME", "churn_db")

DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DB_URL)

# 2. 데이터 로드 및 전처리
CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "model", "final_model.csv")
if not os.path.exists(CSV_PATH):
    print(f"❌ 에러: {CSV_PATH} 파일을 찾을 수 없습니다.")
    exit(1)

df = pd.read_csv(CSV_PATH)
# 프론트엔드 정렬을 위한 날짜 추가 (시뮬레이션 기준일)
df['prediction_date'] = pd.Timestamp('2026-04-01')

# 3. DB 푸시
print(f"🚀 {len(df)}명의 분석 데이터를 churn_predictions 테이블로 전송 중...")
try:
    df.to_sql('churn_prediction', engine, if_exists='replace', index=False)
    print("✅ 완료! 모든 데이터가 성공적으로 푸시되었습니다.")
except Exception as e:
    print(f"❌ DB 푸시 중 에러 발생: {e}")
