import os
import pandas as pd
from sqlalchemy import text
from app.database.connection import get_engine

engine = get_engine()

def clear_tables():
    """외래 키 제약 조건을 잠시 해제하고 테이블 내용을 비웁니다."""
    print("기존 데이터 삭제 중...")
    with engine.connect() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        # 의존성 관계가 있는 테이블들부터 비웁니다.
        tables = ["action_history", "churn_predictions", "transactions", "user_logs", "members"]
        for table in tables:
            conn.execute(text(f"TRUNCATE TABLE {table};"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        conn.commit()
    print("기존 데이터 삭제 완료.")

def load_members():
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'train_members_v2.csv')
    df = pd.read_csv(data_path)
    if "registration_init_time" in df.columns:
        df["registration_init_time"] = pd.to_datetime(
            df["registration_init_time"], errors="coerce"
        ).dt.date
    df.to_sql("members", con=engine, if_exists="append", index=False)
    print(f"members 테이블 {len(df)}건 적재 완료.")

def load_transactions():
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'transactions_v2.csv')
    df = pd.read_csv(data_path)

    for col in ["transaction_date", "membership_expire_date"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.strip()
                .replace({"": None, "nan": None, "None": None})
            )
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    df.to_sql("transactions", con=engine, if_exists="append", index=False)
    print(f"transactions 테이블 {len(df)}건 적재 완료.")

def load_user_logs():
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'user_logs_aug_v2.csv')
    df = pd.read_csv(data_path)
    if "date" in df.columns:
        df = df.rename(columns={"date": "log_date"})
        df["log_date"] = pd.to_datetime(
            df["log_date"], format="%Y%m%d", errors="coerce"
        ).dt.date
    df.to_sql("user_logs", con=engine, if_exists="append", index=False)
    print(f"user_logs 테이블 {len(df)}건 적재 완료.")

if __name__ == "__main__":
    clear_tables()
    load_members()
    load_transactions()
    load_user_logs()
    print("\n[성공] 모든 CSV 데이터 적재가 완료되었습니다.")