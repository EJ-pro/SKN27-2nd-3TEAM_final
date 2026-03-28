"""
metrics.py — KPI 계산 전담 모듈.

책임:
  - 고위험 유저 필터링
  - KPI 수치 계산 (오늘 / 전일 / 델타)
  - 7일 추이 데이터 생성
  - 이탈 주원인 분석

이 모듈은 UI를 알지 못합니다. streamlit / plotly를 import하지 않습니다.
모든 함수는 순수 함수(pure function)에 가깝게 작성합니다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from pages.action_board.config import HIGH_RISK_THRESHOLD, EXPIRY_WINDOW_DAYS, SCALE_FACTOR, TWD_TO_KRW
from pages.action_board.modeling import get_defended_users_count


# ── 데이터 클래스 ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class KPISnapshot:
    """단일 시점의 KPI 스냅샷."""
    high_risk_users: int        # 스케일업 적용 고위험 유저 수
    revenue_at_risk: float      # 스케일업 적용 매출 위기 총액 (원)
    defense_rate: float         # 이탈 방어 성공률 (%)


@dataclass(frozen=True)
class KPIReport:
    """오늘 vs 전일 KPI 비교 리포트."""
    today:     KPISnapshot
    yesterday: KPISnapshot

    @property
    def user_delta(self) -> int:
        return self.today.high_risk_users - self.yesterday.high_risk_users

    @property
    def revenue_delta(self) -> float:
        return self.today.revenue_at_risk - self.yesterday.revenue_at_risk

    @property
    def defense_rate_delta(self) -> float:
        return self.today.defense_rate - self.yesterday.defense_rate


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _filter_high_risk(df: pd.DataFrame, target_date: datetime) -> pd.DataFrame:
    """
    target_date 기준으로 만료 임박 + 이탈 확률 임계값 이상인 유저를 반환합니다.
    """
    if df.empty:
        return df

    window_end = target_date + timedelta(days=EXPIRY_WINDOW_DAYS)
    mask = (
        (df["membership_expire_date"] >= target_date)
        & (df["membership_expire_date"] <= window_end)
        & (df["churn_prob"] >= HIGH_RISK_THRESHOLD)
    )
    return df[mask]


def _snapshot(df: pd.DataFrame, target_date: datetime, seed_offset: int) -> KPISnapshot:
    hr = _filter_high_risk(df, target_date)
    if hr.empty:
        return KPISnapshot(0, 0.0, 0.0)
        
    # 모델로부터 방어 성공 유저 수 획득
    defended_count = get_defended_users_count(hr, seed_offset)
    defense_rate = (defended_count / len(hr)) * 100
    
    return KPISnapshot(
        high_risk_users=len(hr) * SCALE_FACTOR,
        revenue_at_risk=hr["plan_list_price"].sum() * SCALE_FACTOR * TWD_TO_KRW,
        defense_rate=round(defense_rate, 1),
    )


# ── 공개 인터페이스 ───────────────────────────────────────────────────────────

def build_kpi_report(transactions: pd.DataFrame, virtual_today: datetime) -> KPIReport:
    """오늘과 전일 KPI를 계산하여 KPIReport를 반환합니다."""
    yesterday = virtual_today - timedelta(days=1)
    return KPIReport(
        today=_snapshot(transactions, virtual_today, seed_offset=int(virtual_today.timestamp())),
        yesterday=_snapshot(transactions, yesterday, seed_offset=int(yesterday.timestamp())),
    )


def build_trend_data(
    transactions: pd.DataFrame,
    virtual_today: datetime,
    days: int = 7,
) -> pd.DataFrame:
    """
    최근 n일간 고위험 유저 수 및 방어 성공 추이를 DataFrame으로 반환합니다.

    Returns:
        columns: ['날짜', '고위험 유저', '방어 성공 유저']
    """
    rows = []
    
    for i in range(days - 1, -1, -1):
        target = virtual_today - timedelta(days=i)
        hr = _filter_high_risk(transactions, target)
        hr_count = len(hr) * SCALE_FACTOR
        
        # 모델로부터 방어 성공 데이터 획득 (트렌드 일관성)
        defended_count_raw = get_defended_users_count(hr, seed_offset=int(target.timestamp()))
        defended_count = defended_count_raw * SCALE_FACTOR
        
        rows.append({
            "날짜":       target.strftime("%m/%d"),
            "고위험 유저":  hr_count,
            "방어 성공 유저": defended_count,
        })

    return pd.DataFrame(rows)


def build_churn_reasons(df: pd.DataFrame, virtual_today: datetime) -> dict[str, int]:
    """
    고위험 유저들의 이탈 주원인을 데이터 기반으로 집계합니다.
    """
    hr = _filter_high_risk(df, virtual_today)
    if hr.empty:
        return {"데이터 부족": 100}

    # 1. 멤버십 해지 (is_cancel = 1)
    cancel_mask = (hr["is_cancel"] == 1) if "is_cancel" in hr.columns else (hr["msno"] == "none")
    cancel_count = len(hr[cancel_mask])
    
    # 2. 자동결제 해지 (is_auto_renew = 0)
    auto_renew_off_mask = (hr["is_auto_renew"] == 0) & (~cancel_mask)
    auto_renew_off = len(hr[auto_renew_off_mask])
    
    # 3. 장기 미접속 (14일 이상)
    long_term_inactive = 0
    if "last_activity_date" in hr.columns:
        long_term_inactive = len(hr[
            (~cancel_mask) & 
            (hr["is_auto_renew"] == 1) & 
            (hr["last_activity_date"] < virtual_today - timedelta(days=14))
        ])
    
    # 4. 청취 권태기 (낮은 완청곡 수)
    boredom_count = 0
    if "total_100" in hr.columns:
        boredom_count = len(hr[
            (~cancel_mask) & 
            (hr["is_auto_renew"] == 1) & 
            (hr.get("last_activity_date", virtual_today) >= virtual_today - timedelta(days=14)) &
            (hr["total_100"] < 20)
        ])
    
    # 5. 기타
    etc_count = len(hr) - (cancel_count + auto_renew_off + long_term_inactive + boredom_count)
    
    # 결과 취합
    results = {
        "멤버십 해지": cancel_count,
        "자동결제 해지": auto_renew_off,
        "장기 미접속": long_term_inactive,
        "청취 권태기": boredom_count,
        "기타": max(0, etc_count)
    }
    
    total = sum(results.values())
    if total == 0: return {"데이터 부족": 100}
    
    return {k: round((v/total)*100) for k, v in results.items() if v > 0}