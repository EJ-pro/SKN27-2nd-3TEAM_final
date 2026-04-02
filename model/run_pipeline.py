import subprocess
import sys
import os
import time

def run_script(script_path, cwd=None):
    """지정된 스크립트를 실행하고 에러가 발생하면 중단합니다."""
    print(f"\n🚀 실행 중: {os.path.basename(script_path)}")
    print("=" * 40)
    
    start_time = time.time()
    try:
        # 현재 환경의 Python 실행파일 사용
        result = subprocess.run([sys.executable, script_path], check=True, cwd=cwd)
        elapsed = time.time() - start_time
        print(f"✅ 성공! ({elapsed:.2f}초)")
    except subprocess.CalledProcessError as e:
        print(f"❌ 실패: {script_path} 실행 중 에러가 발생했습니다.")
        sys.exit(1)

def main():
    # 0. 프로젝트 루트 경로 및 모델 경로 설정
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    # [추가] 문서 동기화 (Doc/README.md -> root/README.md)
    import shutil
    doc_readme = os.path.join(project_root, 'Doc', 'README.md')
    root_readme = os.path.join(project_root, 'README.md')
    if os.path.exists(doc_readme):
        shutil.copy(doc_readme, root_readme)
        print("📝 문서 동기화 완료: Doc/README.md -> README.md")

    model_dir = os.path.join(project_root, 'model')
    backend_dir = os.path.join(project_root, 'backend')
    ingest_script = os.path.join(backend_dir, 'app', 'ingest', 'db_ingest.py')
    
    print("\n🌸 AI Churn Prediction 통합 파이프라인 가동...")
    print("=" * 60)
    
    # 1. Final Model 실행 (예측 및 모델 앙상블 저장)
    run_script(os.path.join(model_dir, 'final_model.py'), cwd=model_dir)
    
    # 2. Analysis Model 실행 (SHAP 분석 사유 도출)
    run_script(os.path.join(model_dir, 'analysis_model.py'), cwd=model_dir)
    
    # 3. User Future 실행 (Winback 시뮬레이션)
    run_script(os.path.join(model_dir, 'user_future.py'), cwd=model_dir)
    
    # 4. DB Ingestion 실행 (백엔드 연동)
    run_script(ingest_script, cwd=project_root)
    
    print("\n" + "🏆" * 20)
    print("🏆 모든 파이프라인 공정이 성공적으로 종료되었습니다. 🏆")
    print("🏆 이제 프론트엔드 대시보드에서 최신 결과를 확인하세요! 🏆")
    print("🏆" * 20)

if __name__ == "__main__":
    main()
