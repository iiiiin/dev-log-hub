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

    # 1. 블로그 파일 생성 (.md)
    blog_filename = f"{today}-dev-log.md"
    blog_path = os.path.join(root_dir, "blog", "_posts", blog_filename)
    
    body_content = content_json.get('velog', content_json.get('velog_content', '내용 없음'))

    # 블로그용: 리스트로 만들어서 join (들여쓰기 실수 방지)
    blog_lines = [
        "---",
        f'title: "{today} 개발 일지"',
        f"date: {timestamp}",
        "categories: [DevLog]",
        "tags: [TIL]",
        "---",
        "",
        body_content
    ]
    
    with open(blog_path, "w", encoding="utf-8") as f:
        f.write("\n".join(blog_lines))
    print(f"✅ 블로그 파일 생성 완료: {blog_path}")

    # 2. Qiita (CLI용) 파일 생성
    qiita_content = content_json.get('qiita', content_json.get('qiita_content', ''))
    
    if qiita_content:
        lines = qiita_content.split('\n')
        # 제목 추출 및 YAML 깨짐 방지 (따옴표 이스케이프)
        raw_title = lines[0].replace('#', '').strip() if lines else f"{today} 개발 일지"
        safe_title = raw_title.replace('"', '\\"') 
        
        body = '\n'.join(lines[1:]).strip()

        qiita_filename = f"{today}-dev-log.md"
        qiita_path = os.path.join(root_dir, "public", qiita_filename)
        os.makedirs(os.path.dirname(qiita_path), exist_ok=True)

        # ✨ [핵심 수정] 들여쓰기 이슈를 원천 차단하기 위해 리스트 조립 방식 사용
        qiita_lines = [
            "---",
            f'title: "{safe_title}"',
            "tags: [\"DevLog\", \"TIL\"]",
            "private: false",
            f"updated_at: '{timestamp}'",
            "id: null",
            "organization_url_name: null",
            "slide: false",
            "ignorePublish: false",
            "---",
            "",
            body
        ]

        with open(qiita_path, "w", encoding="utf-8") as f:
            f.write("\n".join(qiita_lines))
        print(f"✅ Qiita 파일 생성 완료: {qiita_path}")
    
    # 3. SNS 파일 생성
    sns_path = os.path.join(root_dir, "social", f"{today}.json")
    os.makedirs(os.path.dirname(sns_path), exist_ok=True)

    with open(sns_path, "w", encoding="utf-8") as f:
        json.dump(content_json, f, ensure_ascii=False, indent=2)
    print(f"✅ SNS 파일 생성 완료: {sns_path}")
    
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