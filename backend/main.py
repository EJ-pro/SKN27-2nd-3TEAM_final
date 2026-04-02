from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from datetime import datetime, timedelta
import os
from sqlalchemy import text
from typing import List, Dict, Optional

# Import local modules (relative imports if in a package, or adjust PYTHONPATH)
# For simplicity in this script, we'll redefine the core logic or import if available
try:
    from app.database.connection import get_engine
except ImportError:
    # Fallback/Direct import if structure is different
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), "app"))
    from database.connection import get_engine

app = FastAPI(title="KKBOX Churn Defense API")

# Enable CORS for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with specific origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration (Mirrored from Streamlit config)
SCALE_FACTOR = 1
TWD_TO_KRW = 42
HIGH_RISK_THRESHOLD = 0.60
EXPIRY_WINDOW_DAYS = 3

def _parse_date_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return df
    df = df.copy()
    date_cols = [c for c in df.columns if ("date" in c.lower()) or ("time" in c.lower())]
    for col in date_cols:
        s = df[col].astype(str).str.strip().replace({"nan": None, "None": None, "NaT": None, "": None, "0": None, "00000000": None})
        s = s.str.replace(r"\.0$", "", regex=True)
        parsed = pd.to_datetime(s, format="%Y%m%d", errors="coerce")
        fallback = pd.to_datetime(s, errors="coerce")
        df[col] = pd.to_datetime(parsed.fillna(fallback), errors='coerce') + pd.Timedelta(days=3320)
    return df

def get_data():
    engine = get_engine()
    with engine.connect() as conn:
        members = _parse_date_columns(pd.read_sql(text("SELECT * FROM members"), conn))
        transactions = _parse_date_columns(pd.read_sql(text("SELECT * FROM transactions"), conn))
        try:
            predictions = _parse_date_columns(pd.read_sql(text("SELECT * FROM churn_prediction"), conn))
        except:
            predictions = pd.DataFrame()
            
    # Merge basic info
    if not members.empty and not transactions.empty:
        transactions = pd.merge(transactions, members[["msno", "is_churn"]], on="msno", how="left")
        
    # Inject churn prob (Simplified logic for API)
    if not predictions.empty:
        pred_latest = predictions.sort_values("prediction_date").drop_duplicates("msno", keep="last")
        transactions = pd.merge(transactions, pred_latest[["msno", "churn_probability", "risk_grade"]], on="msno", how="left")
        transactions["churn_prob"] = transactions["churn_probability"].fillna(0.3) # Default fallback
    else:
        transactions["churn_prob"] = 0.1 # Placeholder
        
    return transactions

@app.get("/api/dashboard/kpis")
async def get_kpis(date: Optional[str] = None):
    target_date = datetime.strptime(date, "%Y-%m-%d") if date else datetime.now()
    df = get_data()
    
    def calc_snapshot(d):
        window_end = d + timedelta(days=EXPIRY_WINDOW_DAYS)
        hr = df[(df["membership_expire_date"] >= d) & (df["membership_expire_date"] <= window_end) & (df["churn_prob"] >= HIGH_RISK_THRESHOLD)]
        
        count = len(hr) * SCALE_FACTOR
        # Mock defense rate (replace with real logic if needed)
        defense_rate = 15.5 if count > 0 else 0.0 
        defended_revenue = hr["plan_list_price"].sum() * 0.15 * SCALE_FACTOR * TWD_TO_KRW
        total_potential = hr["plan_list_price"].sum() * SCALE_FACTOR * TWD_TO_KRW
        
        return {
            "high_risk_users": count,
            "revenue_at_risk": total_potential - defended_revenue,
            "defended_revenue": defended_revenue,
            "defense_rate": defense_rate
        }

    today_snap = calc_snapshot(target_date)
    yesterday_snap = calc_snapshot(target_date - timedelta(days=1))
    
    return {
        "today": today_snap,
        "yesterday": yesterday_snap,
        "deltas": {
            "users": today_snap["high_risk_users"] - yesterday_snap["high_risk_users"],
            "revenue": today_snap["revenue_at_risk"] - yesterday_snap["revenue_at_risk"],
            "defense_rate": today_snap["defense_rate"] - yesterday_snap["defense_rate"]
        }
    }

@app.get("/api/dashboard/trends")
async def get_trends(date: Optional[str] = None):
    target_date = datetime.strptime(date, "%Y-%m-%d") if date else datetime.now()
    df = get_data()
    trends = []
    for i in range(6, -1, -1):
        d = target_date - timedelta(days=i)
        window_end = d + timedelta(days=EXPIRY_WINDOW_DAYS)
        hr = df[(df["membership_expire_date"] >= d) & (df["membership_expire_date"] <= window_end) & (df["churn_prob"] >= HIGH_RISK_THRESHOLD)]
        trends.append({
            "date": d.strftime("%m/%d"),
            "high_risk_users": len(hr) * SCALE_FACTOR,
            "defended_users": int(len(hr) * 0.15 * SCALE_FACTOR) # Mock
        })
    return trends

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
