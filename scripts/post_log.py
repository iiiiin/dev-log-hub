import os
import subprocess
import requests
import sys
import datetime
import json       # json 모듈 명시적 import
import textwrap   # ✨ 추가: 들여쓰기 제거용
import re

from dotenv import load_dotenv

# --- [설정 구간] ---
TARGET_REPOS = [
    "/Users/iiiiin/WIP/dev-log-hub",
    "/Users/iiiiin/WIP/turtleneck-macos",
    "/Users/iiiiin/WIP/turtleneck-extension",
    "/Users/iiiiin/WIP/my-dear-extension",
    "/Users/iiiiin/WIP/a-cup-of",
    "/Users/iiiiin/WIP/hop-account",
    "/Users/iiiiin/WIP/cocos-forest",
    "/Users/iiiiin/WIP/portfolio",
]
# ------------------

script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
load_dotenv(os.path.join(root_dir, '.env'))
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

def get_git_changes(repo_path):
    """특정 리포지토리의 오늘 변경사항을 가져옵니다."""
    try:
        if not os.path.exists(repo_path):
            return None

        # 1. 오늘 자정 이후 커밋
        logs = subprocess.check_output(
            ['git', 'log', '--since=midnight', '--pretty=format:- %s'], 
            cwd=repo_path, text=True, stderr=subprocess.DEVNULL
        ).strip()

        # 2. 스테이징된 변경사항 (Diff)
        diff = subprocess.check_output(
            ['git', 'diff', '--cached', '.', ':(exclude)package-lock.json', ':(exclude)*.lock'], 
            cwd=repo_path, text=True, stderr=subprocess.DEVNULL
        ).strip()

        if not logs and not diff:
            return None
            
        return {"name": os.path.basename(repo_path), "logs": logs, "diff": diff}

    except Exception:
        return None

def save_to_file(content_json):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("----- [n8n에서 받은 데이터] -----")
    print(content_json)
    print("-------------------------------")

    # 1. 블로그 파일 생성 (.md) - Velog 내용만 사용
    blog_filename = f"{today}-dev-log.md"
    blog_path = os.path.join(root_dir, "blog", "_posts", blog_filename)
    
    # 키 이름 호환성 체크 (velog_content 또는 velog)
    body_content = content_json.get('velog', content_json.get('velog_content', '내용 없음'))

    # ✨ [수정] textwrap.dedent를 사용하여 Frontmatter의 공백 제거
    blog_content = textwrap.dedent(f"""\
        ---
        title: "{today} 개발 일지"
        date: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        categories: [DevLog]
        tags: [TIL]
        ---

        {body_content}
        """)

    with open(blog_path, "w", encoding="utf-8") as f:
        f.write(blog_content)
    print(f"✅ 블로그 파일 생성 완료: {blog_path}")

    # 2. Qiita (CLI용) 파일 생성 ✨ [신규 추가]
    qiita_content = content_json.get('qiita', content_json.get('qiita_content', ''))
    
    if qiita_content:
        # 제목과 본문 분리 (n8n API용과 달리, CLI는 파일 통째로 씁니다)
        # 다만, AI가 준 내용에서 Frontmatter를 우리가 새로 씌워야 하므로 제목만 추출합니다.
        lines = qiita_content.split('\n')
        title = lines[0].replace('#', '').strip() if lines else f"{today} 개발 일지"
        # 본문은 첫 줄(제목) 제거하고 나머지
        body = '\n'.join(lines[1:]).strip()

        # Qiita CLI용 파일 경로 (public 폴더)
        qiita_filename = f"{today}-dev-log.md"
        qiita_path = os.path.join(root_dir, "public", qiita_filename)
        
        # public 폴더가 없으면 생성
        os.makedirs(os.path.dirname(qiita_path), exist_ok=True)

        # Qiita CLI 전용 Frontmatter 작성
        qiita_file_content = textwrap.dedent(f"""\
            ---
            title: "{title}"
            tags: ["DevLog", "TIL"]
            private: false
            updated_at: '{timestamp}'
            id: null
            organization_url_name: null
            slide: false
            ignorePublish: false
            ---
            {body}
            """)

        with open(qiita_path, "w", encoding="utf-8") as f:
            f.write(qiita_file_content)
        print(f"✅ Qiita 파일 생성 완료: {qiita_path}")
    
    # 2. SNS 파일 생성 (.json) - 전체 데이터(Qiita, X, Threads 포함) 저장
    sns_path = os.path.join(root_dir, "social", f"{today}.json")
    
    # social 폴더가 없으면 생성
    os.makedirs(os.path.dirname(sns_path), exist_ok=True)

    with open(sns_path, "w", encoding="utf-8") as f:
        json.dump(content_json, f, ensure_ascii=False, indent=2)
    print(f"✅ SNS 파일 생성 완료: {sns_path}")
    
    # VS Code로 블로그 글 열기
    try: subprocess.call(["code", blog_path])
    except: pass

if __name__ == "__main__":
    if not N8N_WEBHOOK_URL:
        print("❌ 에러: .env 파일에서 N8N_WEBHOOK_URL을 찾을 수 없습니다.")
        sys.exit(1)

    print("🔍 여러 프로젝트를 순회하며 오늘의 작업을 수집합니다...")
    
    all_logs = []
    all_diffs = []
    active_projects = []

    for repo in TARGET_REPOS:
        data = get_git_changes(repo)
        if data:
            print(f"  👉 감지됨: {data['name']}")
            active_projects.append(data['name'])
            all_logs.append(f"### 📂 Project: {data['name']}\n{data['logs'] if data['logs'] else '커밋 없음'}")
            all_diffs.append(f"### 📂 Project: {data['name']}\n{data['diff'][:3000]}")

    if not active_projects:
        print("📭 오늘은 감지된 변경사항(Staged or Commited)이 없습니다.")
        sys.exit(0)

    print(f"\n🚀 총 {len(active_projects)}개 프로젝트의 내용을 AI(n8n)에게 보냅니다...")

    payload = {
        "logs": "\n\n".join(all_logs),
        "diff": "\n\n".join(all_diffs),
        "project": f"Multi-Repo Work ({', '.join(active_projects)})"
    }

    try:
        response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            save_to_file(result)
            print("\n✨ 모든 작업이 완료되었습니다! 생성된 파일을 확인하고 Push하세요.")
        else:
            print(f"❌ n8n 에러: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"❌ 통신 에러: {e}")