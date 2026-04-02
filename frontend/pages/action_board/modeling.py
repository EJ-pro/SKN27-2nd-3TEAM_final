"""
modeling.py — 이탈 방어 성공 및 확률 예측 모델 (Logic-based).

책임:
  - 고위험 유저의 '방어 성공 확률' 계산 (Inference)
  - 유저 특성(is_auto_renew, log 등)에 따른 가중치 부여

이 모듈은 향후 실제 ML 모델(.pkl)로 교체하기 전의 '비즈니스 로직 기반 모델' 역할을 합니다.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

def predict_defense_probability(df: pd.DataFrame) -> pd.Series:
    """
    유저별 특징을 기반으로 '이탈 방어 성공 확률'을 반환합니다.
    
    로직:
    - 자동결제 유지 유저: 기본 성공률 높음 (60%~90%)
    - 자동결제 해지 유저: 기본 성공률 낮음 (10%~40%)
    - 과거 Churn 경험 없음(is_churn=0): 가산점 (+10%)
    - 결제 금액이 높음: 가산점 (+5%)
    """
    if df.empty:
        return pd.Series(dtype=float)

    rng = np.random.default_rng(42)
    n = len(df)
    
    # 기본 확률 (스켈레톤)
    # is_auto_renew 가 1이면(유지) 방어 성공 가능성이 이미 높음
    base_probs = df["is_auto_renew"].apply(
        lambda x: rng.uniform(0.6, 0.9) if x == 1 else rng.uniform(0.1, 0.4)
    )
    
    # 가산점 1: 과거 이탈 경험 없음
    if "is_churn" in df.columns:
        base_probs += df["is_churn"].apply(lambda x: 0.1 if x == 0 else -0.05)
        
    # 가산점 2: 결제 금액 (상대적 충성도)
    if "plan_list_price" in df.columns:
        mean_price = df["plan_list_price"].mean()
        if mean_price > 0:
            base_probs += (df["plan_list_price"] / mean_price) * 0.05
            
    # 확률 범위 제한 (0.0 ~ 1.0)
    return base_probs.clip(0.01, 0.99)

def get_defended_users_mask(df: pd.DataFrame, seed_offset: int = 0) -> pd.Series:
    """
    고위험 유저 리스트를 받아, 모델 확률에 따라 각 유저의 '방어 성공 여부'를 Boolean Mask로 반환합니다.
    """
    if df.empty:
        return pd.Series(dtype=bool)
    
    probs = predict_defense_probability(df)
    rng = np.random.default_rng(seed_offset)
    
    # 각 유저별로 확률 시행 (Monte Carlo)
    results = rng.random(len(df)) < probs
    return pd.Series(results, index=df.index)

def get_defended_users_count(df: pd.DataFrame, seed_offset: int = 0) -> int:
    """
    고위험 유저 리스트를 받아, 최종 방어 성공 유저 수를 반환합니다.
    """
    mask = get_defended_users_mask(df, seed_offset)
    return int(mask.sum())
