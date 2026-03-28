# Streamlit 실행 가이드

이 문서는 프로젝트의 프론트엔드(Streamlit) 환경을 처음 설정하고 실행하는 과정을 설명합니다.

## 1. 사전 준비
- **Python 3.9 이상** 버전이 설치되어 있어야 합니다.

## 2. 가상 환경 설정
프로젝트 루트 디렉토리에서 아래 명령어를 실행하여 가상 환경을 만들고 활성화합니다.

```powershell
# 가상 환경 생성 (root 폴더에서 실행)
python -m venv .venv

# 가상 환경 활성화 (Windows)
.\.venv\Scripts\activate
```

## 3. 의존성 설치
프로젝트 실행에 필요한 패키지들을 설치합니다.

```powershell
pip install -r requirements.txt
```

## 4. 프론트엔드 실행
`frontend` 폴더로 이동한 후 Streamlit 서버를 실행합니다.

```powershell
# frontend 폴더로 이동
cd frontend

# Streamlit 실행
streamlit run app.py
```

## 참고 사항
- 실행 후 브라우저에서 `http://localhost:8501`로 접속하여 결과를 확인할 수 있습니다.
- `app.py`는 프론트엔드의 메인 엔트리 포인트입니다.
