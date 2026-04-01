import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

def ingest_to_mysql():
    # 1. 환경 변수 로드
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    load_dotenv(env_path)
    
    db_user = os.getenv("DB_USER", "appuser")
    db_pass = os.getenv("DB_PASSWORD", "app1234")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "3307")
    db_name = os.getenv("DB_NAME", "churn_db")
    
    # SQLAlchemy 엔진 생성
    connection_string = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    engine = create_engine(connection_string)
    
    print(f"🔗 DB 연결 시도 중: {db_host}:{db_port}")
    
    # 2. 업로드할 파일 리스트
    model_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'model')
    files_to_ingest = {
        'analysis_model.csv': 'churn_analysis_results',
        'churn_risk_result.csv': 'churn_risk_results'
    }
    
    for filename, table_name in files_to_ingest.items():
        file_path = os.path.join(model_dir, filename)
        
        if os.path.exists(file_path):
            print(f"🚀 {filename} -> {table_name} 적재 중...")
            df = pd.read_csv(file_path)
            
            # DB 적재 (기존 데이터 Replace)
            df.to_sql(name=table_name, con=engine, if_exists='replace', index=False)
            print(f"✅ {table_name} 적재 완료! (총 {len(df)}행)")
        else:
            print(f"⚠️ Warning: {filename} 파일을 찾을 수 없어 건너뜁니다.")

if __name__ == "__main__":
    try:
        ingest_to_mysql()
        print("\n🏆 모든 데이터 백엔드 연동 성공!")
    except Exception as e:
        print(f"\n❌ DB 적재 실패: {e}")
