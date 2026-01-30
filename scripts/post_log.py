import os
import subprocess
import requests
import sys
from dotenv import load_dotenv

# 1. .env 파일 로드 (보안)
# 스크립트 실행 위치에 관계없이 루트의 .env를 찾도록 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
load_dotenv(os.path.join(root_dir, '.env'))

# 환경변수에서 n8n 주소 가져오기
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

def get_git_info():
    """Git 로그와 변경사항을 가져옵니다."""
    try:
        # A. 오늘 자정부터 지금까지의 커밋 메시지 (내가 뭘 했는지 요약)
        logs = subprocess.check_output(
            ['git', 'log', '--since=midnight', '--pretty=format:- %s'], 
            text=True
        ).strip()

        # B. 현재 스테이징된 변경사항 (코드의 구체적 내용)
        # 너무 긴 파일(lock 파일 등)은 제외하여 토큰 절약
        diff = subprocess.check_output(
            ['git', 'diff', '--cached', '.', ':(exclude)package-lock.json', ':(exclude)*.lock'], 
            text=True
        ).strip()
        
        return logs, diff
    except subprocess.CalledProcessError:
        print("⚠️ Git 정보를 가져오는 데 실패했습니다. Git 저장소가 맞나요?")
        return None, None

def send_to_n8n(logs, diff):
    """n8n으로 데이터를 전송합니다."""
    if not logs and not diff:
        print("📭 변경된 내용(Diff)이나 오늘의 커밋(Log)이 없습니다.")
        print("   (팁: 'git add'를 먼저 하셨나요?)")
        return

    # 데이터가 너무 많으면 AI가 힘들어하므로 적당히 자름 (선택사항)
    if len(diff) > 15000:
        diff = diff[:15000] + "\n... (내용이 너무 길어 생략됨)"

    payload = {
        "logs": logs if logs else "오늘 커밋 없음",
        "diff": diff if diff else "코드 변경 없음 (문서 작업 등)",
        "project": "dev-log-hub", # 프로젝트명 식별자
        "author": "iiiiin"
    }

    print("🚀 n8n으로 데이터를 전송합니다...")
    
    try:
        response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=10)
        
        if response.status_code == 200:
            print("✅ 성공! 초안 작성이 요청되었습니다.")
        else:
            print(f"❌ 실패: 서버 응답 코드 {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ 전송 중 에러 발생: {e}")

if __name__ == "__main__":
    # 보안 체크
    if not N8N_WEBHOOK_URL:
        print("❌ 에러: .env 파일에 'N8N_WEBHOOK_URL'이 없습니다.")
        sys.exit(1)

    print("🔍 작업 내용을 수집 중입니다...")
    logs, diff = get_git_info()
    send_to_n8n(logs, diff)