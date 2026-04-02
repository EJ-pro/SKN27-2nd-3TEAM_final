import os
import joblib
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import roc_auc_score

# ==========================================
# 0. 사유 및 카테고리 매핑 (Reason & Category Mapping)
# ==========================================
REASON_MAP = {
    'is_auto_renew': '자동결제 미설정',
    'is_cancel': '서비스 취소 요청',
    'payment_plan_days': '단기 결제 플랜',
    'actual_amount_paid': '결제 금액 특이',
    'plan_list_price': '플랜 가격 요인',
    'trans_count': '구독 갱신 부족',
    'payment_method_id': '결제수단 특성',
    'active_days': '활동 빈도 저조',
    'total_secs': '재생 시간 부족',
    'tenure': '가입 기간 특성',
    'num_25': '단기 청취 위주',
    'num_50': '반절 청취 위주',
    'num_75': '미리듣기형 청취',
    'num_985': '완청 직전 중단',
    'num_100': '완청 횟수 부족',
    'completion_ratio': '완청 비율 저조',
    'unique_ratio': '청취 다양성 부족',
    'total_songs': '스트리밍 곡 부족',
    'city': '지역 특성',
    'registered_via': '가입 경로 특성',
    'bd': '연령대 특성',
    'gender': '성별 특성',
    'None': '기타 사유'
}

CATEGORY_MAP = {
    'is_auto_renew': '결제 및 구독', 'is_cancel': '결제 및 구독', 'payment_plan_days': '결제 및 구독',
    'actual_amount_paid': '결제 및 구독', 'plan_list_price': '결제 및 구독', 'trans_count': '결제 및 구독',
    'payment_method_id': '결제 및 구독',
    'active_days': '활동 및 참여', 'total_secs': '활동 및 참여', 'tenure': '활동 및 참여',
    'num_25': '활동 및 참여', 'num_50': '활동 및 참여', 'num_75': '활동 및 참여',
    'num_985': '활동 및 참여', 'num_100': '활동 및 참여',
    'completion_ratio': '콘텐츠 이용 습관', 'unique_ratio': '콘텐츠 이용 습관', 'total_songs': '콘텐츠 이용 습관',
    'city': '사용자 프로필', 'registered_via': '사용자 프로필', 'bd': '사용자 프로필',
    'gender': '사용자 프로필',
    'None': '기타'
}

def get_base_feature_name(col):
    """OHE 컬럼에서 원본 피처명을 추출합니다."""
    for base in REASON_MAP.keys():
        if col.startswith(f"{base}_") or col == base:
            return base
    return col

def finalize_features_consistent(df):
    """통합 파이프라인과 동일한 피처 전처리를 수행합니다."""
    # msno, is_churn 등 제외
    X = df.drop(columns=['msno', 'is_churn', 'registration_init_time'], errors='ignore')
    # 범주형 OHE (final_model.py와 동일한 체계 유지)
    X = pd.get_dummies(X, columns=['city', 'registered_via', 'payment_method_id_last', 'gender'], drop_first=True)
    return X.fillna(0).astype(float)

def run_analysis_pipeline():
    """메인 분석 파이프라인 실행 함수"""
    print("\n🔍 [분석 단계] 고위험군 상세 이탈 사유 도출 중...")
    BASE_DIR = os.path.dirname(__file__)
    
    # 1. 통합 데이터 로드 (final_model.py의 로직 재사용)
    from final_model import build_modeling_dataframe
    merge_df, _ = build_modeling_dataframe()
    
    # 2. 미리 학습된 통합 모델 로드
    model_path = os.path.join(BASE_DIR, 'final_model.joblib')
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"❌ 통합 모델 파일을 찾을 수 없습니다: {model_path}. final_model.py를 먼저 실행하세요.")
    models = joblib.load(model_path)
    
    # 3. 통합 예측 결과 로드 (일관성 유지)
    pred_path = os.path.join(BASE_DIR, 'final_model.csv')
    if not os.path.exists(pred_path):
        raise FileNotFoundError(f"❌ 통합 예측 결과 파일을 찾을 수 없습니다: {pred_path}")
    final_preds = pd.read_csv(pred_path)

    # 4. 피처 정비 및 기여도 계산
    X = finalize_features_consistent(merge_df)
    
    print("📈 앙상블 기여도(SHAP Contrib) 기반 사유 분석 중...")
    all_contribs = []
    for m in models:
        # XGBoost의 pred_contribs 기능을 활용하여 SHAP 스타일의 기여도 계산
        contribs = m.get_booster().predict(xgb.DMatrix(X), pred_contribs=True)
        all_contribs.append(contribs[:, :-1])
    
    mean_contribs = np.mean(all_contribs, axis=0)
    feature_names = X.columns.tolist()

    reasons_list = []
    for i in range(len(mean_contribs)):
        user_contrib = mean_contribs[i]
        sorted_indices = np.argsort(user_contrib)[::-1]
        
        user_reasons = []
        for idx in sorted_indices[:3]:
            # 기여도가 양수인 상위 3개 지표 추출
            if user_contrib[idx] > 0:
                base_name = get_base_feature_name(feature_names[idx])
                user_reasons.append(base_name)
            else:
                user_reasons.append("None")
        while len(user_reasons) < 3: user_reasons.append("None")
        reasons_list.append(user_reasons)

    # 5. 결과 필터링 및 한글 매핑
    analysis_df = pd.merge(final_preds[['msno', 'churn_probability']], 
                          pd.DataFrame(reasons_list, columns=['r1', 'r2', 'r3'], index=final_preds.index),
                          left_index=True, right_index=True)
    
    for i in range(1, 4):
        analysis_df[f'reason_{i}'] = analysis_df[f'r{i}'].map(REASON_MAP).fillna(analysis_df[f'r{i}'])
        analysis_df[f'category_{i}'] = analysis_df[f'r{i}'].map(CATEGORY_MAP).fillna('기타')
    
    output_path = os.path.join(BASE_DIR, 'analysis_model.csv')
    # 임시 컬럼 제거 후 저장
    analysis_df.drop(columns=['r1', 'r2', 'r3']).to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"✨ [완료] 최종 분석 리포트 생성 완료: {output_path}")

if __name__ == "__main__":
    try:
        run_analysis_pipeline()
    except Exception as e:
        import traceback
        print(f"❌ 분석 엔진 중단: {e}")
        traceback.print_exc()