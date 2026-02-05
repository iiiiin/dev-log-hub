# Dev Log Hub (Automated TIL System)

**Dev Log Hub**는 로컬 개발 기록(Git Commit & Diff)을 AI가 자동으로 분석하여, 기술 블로그(GitHub Pages/Velog)와 Qiita(일본 기술 블로그)에 배포 가능한 형태로 가공해주는 자동화 파이프라인입니다.

## 🚀 Key Features

- **Automated Drafting:** `til` 명령어 하나로 당일 작업한 여러 Git 리포지토리를 스캔하여 개발 일지 초안 생성.
- **Multi-Platform Support:**
  - 🇰🇷 **GitHub Pages (Jekyll):** 한국어 기술 블로그 포맷 (.md)
  - 🇯🇵 **Qiita:** 일본어 기술 블로그 포맷 (.md) + CLI 자동 배포
  - 🧵 **SNS (Planned):** 추후 X(Twitter) 및 Threads API 연동 예정
- **AI-Powered:** Google Gemini 1.5 Flash 모델을 사용하여 문맥을 파악하고 요약.

---

## 🛠 Architecture & Decisions (기술적 의사결정)

이 프로젝트는 **"학습(Learning)"**과 **"효율성(Efficiency)"** 사이에서 점진적으로 진화했습니다.

### Phase 1: Prototype with n8n & Docker
초기에는 **n8n(Low-code automation)**을 도입하여 로컬 자동화 서버를 구축했습니다.
- **Docker:** n8n을 컨테이너 환경에서 독립적으로 구동.
- **ngrok:** 로컬 Webhook URL을 외부(GitHub)와 연결하기 위한 터널링.
- **Workflow:** Git Push → ngrok → n8n → AI Summary → Deploy.

```mermaid
graph LR
    subgraph Local["Local Environment (MacBook)"]
        direction LR
        ngrok["ngrok<br/>(Tunnel)"]
        subgraph Docker
            n8n[n8n Server]
        end
    end
    GH[GitHub Actions] -->|Webhook| ngrok
    ngrok --> n8n
    n8n -->|API| Gemini[Google Gemini]
    
    style Local fill:#f9f9f9,stroke:#333
    style Docker fill:#e3f2fd,stroke:#2196f3,stroke-dasharray: 5 5
    style n8n fill:#ffcdd2,stroke:#f44336
```
### Phase 2: Optimization with Python (Current) ⚡️
운영 효율성을 위해 Python 스크립트 단독 실행 구조로 경량화했습니다.

변경점: n8n 서버 제거, Python 스크립트(post_log.py) 내에서 Gemini API 직접 호출.

이점:
- 실행 속도 향상 및 시스템 리소스 절약 (Docker/ngrok 불필요).
- til 명령어 한 번으로 즉시 실행 가능.

코드 스니펫

```mermaid
graph LR
    User[Developer] -->|Run 'til'| Script["Python Script<br/>(post_log.py)"]
    Script -->|Collect Logs| Git[Local Git Repos]
    Script -->|Generate Text| Gemini[Google Gemini API]
    Script -->|Create Files| Files[Markdown Files]
    Files -->|Git Push| GH_Actions[GitHub Actions]
    GH_Actions -->|Publish| Qiita[Qiita Blog]
    GH_Actions -->|Build| Pages[GitHub Pages]

    style Script fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    style GH_Actions fill:#24292e,stroke:#fff,color:#fff
```

📦 Project Structure

```bash
.
├── blog/             # GitHub Pages (Jekyll) 포스트 저장소
├── public/           # Qiita CLI 배포용 저장소
├── scripts/
│   └── post_log.py   # 메인 자동화 스크립트
├── .github/
│   └── workflows/
│       └── qiita-publish.yml # Qiita 자동 배포 파이프라인
└── n8n_backup/       # (Archived) n8n 워크플로우 백업
```

🚀 How to Use

1. Setup
```bash
pip install -r requirements.txt
npm install
```

2. Run
```bash
# 오늘 작업한 내용을 스캔하여 글 생성
til 
# 또는 python scripts/post_log.py
```

3. Publish

```bash
git add .
git commit -m "feat: today's dev log"
git push origin main
```
