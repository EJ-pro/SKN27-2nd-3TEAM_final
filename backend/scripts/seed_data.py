import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from sqlalchemy import text
from app.database.connection import get_engine

engine = get_engine()

BASE_PATH = "/app/data/raw"   # 도커 컨테이너 기준 경로

def load_members():
    df = pd.read_csv(f"{BASE_PATH}/train_members_v2.csv")

    if "registration_init_time" in df.columns:
        df["registration_init_time"] = pd.to_datetime(
            df["registration_init_time"], errors="coerce"
        ).dt.date

    df.to_sql("members", con=engine, if_exists="append", index=False)
    print(f"members 적재 완료: {len(df)}건")


def load_transactions():
    df = pd.read_csv(f"{BASE_PATH}/transactions_v2.csv")

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
    print(f"transactions 적재 완료: {len(df)}건")


def load_user_logs():
    df = pd.read_csv(f"{BASE_PATH}/user_logs_aug_v2.csv")

    if "date" in df.columns:
        df = df.rename(columns={"date": "log_date"})
        df["log_date"] = pd.to_datetime(
            df["log_date"].astype(str), format="%Y%m%d", errors="coerce"
        ).dt.date

    df.to_sql("user_logs", con=engine, if_exists="append", index=False)
    print(f"user_logs 적재 완료: {len(df)}건")


def load_churn_prediction():
    df = pd.read_csv(f"{BASE_PATH}/churn_prediction.csv")
    df = df[["msno", "churn_probability"]].copy()

    df.to_sql("churn_prediction", con=engine, if_exists="append", index=False)
    print(f"churn_prediction 적재 완료: {len(df)}건")


def load_churn_predict_reason():
    df = pd.read_csv(f"{BASE_PATH}/churn_predict_reason.csv")
    df = df[
        [
            "msno",
            "churn_probability",
            "reason_1",
            "category_1",
            "reason_2",
            "category_2",
            "reason_3",
            "category_3",
        ]
    ].copy()

    df.to_sql("churn_predict_reason", con=engine, if_exists="append", index=False)
    print(f"churn_predict_reason 적재 완료: {len(df)}건")


def load_churn_risk_result():
    df = pd.read_csv(f"{BASE_PATH}/churn_risk_result.csv")
    df = df[["msno", "churn_proba", "risk_score", "risk_grade"]].copy()

    df.to_sql("churn_risk_result", con=engine, if_exists="append", index=False)
    print(f"churn_risk_result 적재 완료: {len(df)}건")


from sqlalchemy import text

def truncate_all_tables():
    tables = [
        "churn_risk_result",
        "churn_predict_reason",
        "churn_prediction",
        "user_logs",
        "transactions",
        "members",
    ]

    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0;"))

        for table in tables:
            exists = conn.execute(text(f"SHOW TABLES LIKE '{table}';")).fetchone()
            if exists:
                conn.execute(text(f"TRUNCATE TABLE {table};"))
                print(f"{table} 비우기 완료")
            else:
                print(f"{table} 없음 -> 건너뜀")

        conn.execute(text("SET FOREIGN_KEY_CHECKS=1;"))


if __name__ == "__main__":
    # 필요하면 먼저 비우고 다시 적재
    truncate_all_tables()

    load_members()
    load_transactions()
    load_user_logs()
    load_churn_prediction()
    load_churn_predict_reason()
    load_churn_risk_result()

    print("CSV 데이터 적재 완료")