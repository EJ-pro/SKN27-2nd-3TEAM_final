## KKBOX 구독자 이탈 예측 및 방지 시스템 (Churn Prevention System)
- KKBOX 데이터를 활용하여 이탈 위험 고객을 조기에 감지하고, 맞춤형 마케팅 액션을 시뮬레이션하여 비즈니스 손실을 최소화하는 솔루션입니다.

## 프로젝트 개요   
- 배경
> 디지털 음악 스트리밍 산업은 고도의 성숙 단계에 진입했으며, 신규 고객 유치 비용(CAC, Customer Acquisition Cost)이 기존 고객 유지 비용(CRC, Customer Retention Cost)보다 훨씬 높게 발생하는 구독 경제 서비스를 기반으로 합니다. 대만인 사용자를 대상으로 한 KKBOX 역시 수백만 명의 사용자를 보유하고 있으나, 경쟁 서비스(Spotify, Apple Music 등)의 확대로 인해 고객 유지율(Retention Rate) 관리가 서비스 성장의 핵심 지표가 되었습니다.

- 목적
> 본 프로젝트의 주된 목적은 머신러닝 모델을 활용하여 이탈 가능성이 높은 사용자를 선제적으로 식별하고, 데이터 기반의 이탈 방지 전략을 수립하는 데 있습니다.

- 데이터 소개
> 데이터 수집 경로(kkbox), 데이터 설명

##  기술 스택   

### Language
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

### Data Analysis
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white)

### Visualization
![Matplotlib](https://img.shields.io/badge/Matplotlib-11557C?style=for-the-badge&logo=plotly&logoColor=white)
![Seaborn](https://img.shields.io/badge/Seaborn-4C72B0?style=for-the-badge&logoColor=white)

### Machine Learning
![XGBoost](https://img.shields.io/badge/XGBoost-218EBB?style=for-the-badge&logo=xgboost&logoColor=white)
![Scikit-Learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)

### Frontend & Library
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)

### Tool
![Google Colab](https://img.shields.io/badge/Google%20Colab-F9AB00?style=for-the-badge&logo=googlecolab&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![PyMySQL](https://img.shields.io/badge/PyMySQL-4479A1?style=for-the-badge&logo=python&logoColor=white)<!-- Git -->
![Git](https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white)
![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)
![Notion](https://img.shields.io/badge/Notion-000000?style=for-the-badge&logo=notion&logoColor=white)
![Figma](https://img.shields.io/badge/Figma-F24E1E?style=for-the-badge&logo=figma&logoColor=white)

### DevOps & Infrastructure
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Docker Compose](https://img.shields.io/badge/Docker%20Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
   
## WBS (Work Breakdown Structure)
| 작업                           | 3/26 | 3/27 | 3/28 | 3/29 | 3/30 | 3/31 | 4/1 | 4/2 |
| ----------------------------| ---- | ---- | ---- | ---- | ---- | ---- | --- | --- |
| 요구사항 정의서 작성           | ███  | ███  | ███  |      |      |      |     |     |
| 화면설계서 작성                | ███  | ███  | ███  |      |      |      |     |     |
| ERD 설계                       | ███  | ███  | ███  |      |      |      |     |     |
| 데이터 수집                    | ███  | ███  |      |      |      |      |     |     |
| 데이터 전처리                  |      | ███  | ███  | ███  | ███  | ███  | ███ |     |
| 모델링 & 실험                  |      |      |      | ███  | ███  | ███  | ███ |     |
| 백엔드 개발                    |      |      |      |       | ███  |     |      |     |
| 프론트 개발                    |      |      |███   | ███  |       |     |      |     |
| 프론트&백엔드 연결 및 통합 테스트|      |      |      |      |      |       | ███ |  ███ |
| 발표 준비                      |      |      |      |      |      |      | ███ | ███ |
   

<br>   

## 데이터 전처리 결과서 (EDA)
## 1. 전체 구조
세 모델 모두 아래 순서로 동일하게 진행됩니다.
1. 데이터 로드
2. 기본 전처리
3. transactions 변수 생성
4. 결제 후 첫 청취 변수 생성
5. user_logs 변수 생성
6. 전체 데이터 병합
7. 모델별 전처리
8. 5-fold Stratified CV
9. test 확률 평균 앙상블
10. confusion matrix / feature importance / prediction csv 저장

---

## 2. 변수 블록 설명

-> 기존 변수, 새로 생성 변수 분리해서 설명하기

### A. train_members 원본 변수
- `city`: 거주 도시. 사용자 지역 특성을 반영합니다.
- `bd`: 나이. 비정상값(0 이하, 100 이상)은 중앙값으로 대체합니다.
- `gender`: 성별. female=0, male=1로 변환합니다.
- `registered_via`: 가입 채널. 가입 경로에 따른 잔존 차이를 반영합니다.
- `registration_init_time`: 최초 가입일. 이후 `tenure` 변수 생성에 사용됩니다.
- `tenure`: 기준일 직전까지 서비스에 머문 기간. 오래 쓴 사용자인지 파악합니다.

### B. 할인 / 가격 관련 거래 변수
- `discount_amount`: 정가 - 실제 결제금액. 할인 절대 크기입니다.
- `discount_rate`: 할인율. 할인 의존 결제 패턴을 잡습니다.
- `has_discount`: 할인 여부(0/1).
- `discount_rate_mean`: 전체 거래 기준 평균 할인율.
- `discount_rate_last`: 가장 최근 거래 할인율.
- `has_discount_rate`: 전체 거래 중 할인 거래 비율.

### C. 최근 거래 상태 변수
- `payment_method_id_last`: 최근 결제 수단.
- `payment_method_id_nunique`: 결제 수단 변경 다양성.
- `payment_plan_days_last`: 최근 결제 구독 기간.
- `payment_plan_days_mean`: 전체 평균 구독 기간.
- `payment_plan_days_std`: 구독 기간 변동성.
- `actual_amount_paid_last`: 최근 실제 결제금액.
- `actual_amount_paid_mean`: 전체 평균 실제 결제금액.
- `actual_amount_paid_std`: 결제금액 변동성.
- `plan_list_price_last`: 최근 정가.
- `is_auto_renew_last`: 최근 자동갱신 여부.
- `is_auto_renew_rate`: 전체 거래 중 자동갱신 비율.
- `is_cancel_last`: 최근 결제 취소 여부.
- `is_cancel_rate`: 전체 거래 중 취소 비율.
- `trans_count`: 전체 거래 횟수.
- `days_since_last_txn`: 마지막 결제 후 얼마나 지났는지.
- `days_until_expire`: 기준일 기준 만료일까지 남은 일수.
- `last_payment_gap`: 마지막 결제일과 마지막 만료일 사이 간격.
- `txn_span_days`: 첫 거래부터 마지막 거래까지 전체 거래 기간.
- `expiry_before_cutoff_flag`: 기준일 이전에 이미 만료되었는지 여부.

### D. 최근 2회 거래 변화량 변수
- `actual_paid_change_last2`: 최근 2회 실제 결제금액 차이.
- `plan_days_change_last2`: 최근 2회 구독일수 차이.
- `txn_gap_last2`: 최근 2회 결제일 사이 간격.
- `expire_gap_change_last2`: 최근 2회 만료일 차이.

### E. 결제 후 첫 청취 변수
- `mean_days_to_first_listen_after_txn`: 평균적으로 결제 후 첫 청취까지 걸린 시간.
- `last_days_to_first_listen_after_txn`: 최근 결제 후 첫 청취까지 걸린 시간.
- `listen_within_7d_after_txn_rate`: 전체 결제 중 7일 이내 청취 비율.
- `listen_within_30d_after_txn_rate`: 전체 결제 중 30일 이내 청취 비율.

### F. 전체 로그 변수
- `active_days_all`: 전체 기간 실제 활동 일수.
- `num_25_all`, `num_50_all`, `num_75_all`, `num_985_all`, `num_100_all`: 재생 구간별 누적 횟수.
- `num_unq_all`: 전체 기간 고유곡 수.
- `total_secs_all`: 전체 청취 시간.
- `total_secs_mean_all`: 평균 청취 시간.
- `play_total_all`: 전체 재생 횟수 합.
- `completion_ratio_all`: 완청 비율.
- `unique_ratio_all`: 고유곡 비율.

### G. 최근 7일 / 30일 로그 변수
- `active_days_7`, `active_days_30`: 최근 창에서 실제 활동 일수.
- `total_secs_7`, `total_secs_30`: 최근 창 총 청취시간.
- `total_secs_mean_7`, `total_secs_mean_30`: 최근 창 평균 청취시간.
- `play_total_7`, `play_total_30`: 최근 창 총 재생횟수.
- `num_unq_7`, `num_unq_30`: 최근 창 고유곡 수.
- `completion_ratio_7`, `completion_ratio_30`: 최근 창 완청 비율.
- `unique_ratio_7`, `unique_ratio_30`: 최근 창 고유곡 비율.

---

## 3. 출력 결과 해석
- `Fold별 AUC`: 각 fold validation AUC
- `Mean CV AUC`: 평균 성능
- `Std CV AUC`: fold 간 편차
- `OOF AUC`: 학습셋 기준 전체 교차검증 AUC
- `Final Test AUC`: test 확률 평균 결과
- `pred_prob_is_churn`: churn 확률
- `pred_is_churn_threshold_04`: threshold 0.4 기준 최종 분류
- `pred_is_churn`: 위와 동일한 최종 예측 레이블
<br>   
   
## Target Variable (예측 목표)

>인용문   
   
<details><summary>접고 펴는 기능
</summary>

*Write here!*
</details>

- EASYME.md를 드래그하고 상단에 `Aa` 아이콘을 누르면? 👉 Easyme.md   
- EASYME.md를 드래그하고 상단에 `A` 아이콘을 누르면? 👉 EASYME.MD   
- EASYME.md를 드래그하고 상단에 `a` 아이콘을 누르면? 👉 easyme.md   
   
<br>   
## 활용 모델
1. 
2.
3.
   
## 모델 성능 평가 비교   
### Table of contents
1. [title1](#write-title-here!)   
2. [title2](#only-lowercase)   
3. [title3](#use"-"instead-of-spacing-words)   
4. [title4](#example)   
    - [❓ EASYME.md가 뭐예요?](#-easymemd가-뭐예요)   
    - [🛠 기능 엿보기](#-기능-엿보기)
   
### Unordered list   
- unordered list1   
- unordered list2   
- unordered list3   
- unordered list4   
   
### Ordered list   
1. ordered list1   
2. ordered list2   
3. ordered list3   
4. ordered list4   
   
<br>   
   
## 결론   
### General link
- [🚗 Visit EASYME.md's Repo](https://github.com/EASYME-md/client)   
- [🙋‍♂️ Visit ONE:A's Github](https://github.com/onealog)

### Image link
![onealog](/assets/readme/easyme.png)   
   
<br>   
   
## Code Block   
### Code inline
- `console.log('Hello EASYME.md!');`   
   
### Code block
```js
function makeDeveloper(name, language) {
  if (name === 'ONE:A' && language === 'JavaScript') {
    return 'perfect!';
  }

  return false;
}

makeDeveloper('ONE:A', 'JavaScript');
```

<br>   
   
## Table   


| title1 | title2 | title3 |
| --- | --- | --- |
| 1 | 2 | 3 |
| 4 | 5 | 6 |
| 7 | 8 | 9 |


<br>   
