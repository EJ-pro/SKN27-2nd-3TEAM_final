import pandas as pd
from app.database.connection import get_engine

engine = get_engine()

def load_members():
    df = pd.read_csv(r"C:\dev\Project\SKN27-2nd-3TEAM\backend\data\raw\train_members_v2.csv")
    if "registration_init_time" in df.columns:
        df["registration_init_time"] = pd.to_datetime(
            df["registration_init_time"], format="%Y%m%d", errors="coerce"
        ).dt.date
    df.to_sql("members", con=engine, if_exists="append", index=False)

def load_transactions():
    df = pd.read_csv(r"C:\dev\Project\SKN27-2nd-3TEAM\backend\data\raw\transactions_v2.csv")
    for col in ["transaction_date", "membership_expire_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format="%Y%m%d", errors="coerce").dt.date
    df.to_sql("transactions", con=engine, if_exists="append", index=False)

def load_user_logs():
    df = pd.read_csv(r"C:\dev\Project\SKN27-2nd-3TEAM\backend\data\raw\user_logs_aug_v2.csv")
    if "date" in df.columns:
        df = df.rename(columns={"date": "log_date"})
        df["log_date"] = pd.to_datetime(
            df["log_date"], format="%Y%m%d", errors="coerce"
        ).dt.date
    df.to_sql("user_logs", con=engine, if_exists="append", index=False)

if __name__ == "__main__":
    load_members()
    load_transactions()
    load_user_logs()
    print("CSV 데이터 적재 완료")