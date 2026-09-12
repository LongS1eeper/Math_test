# 인터넷에 올리기

두 가지 길이 있습니다. **A로 먼저 올리고, 나중에 필요하면 B로 한 줄만 추가**하면 됩니다.
코드는 그대로입니다.

| | A · 그냥 올리기 | B · 외부 DB 추가 |
|---|---|---|
| 준비물 | GitHub + Streamlit Cloud | + Neon 계정 |
| 걸리는 시간 | 15분 (+토큰 3분) | +10분 |
| 시험지·해설 | 저장소에 누적 — 앱에서 올리면 자동 커밋 | DB에 저장 |
| 성적·오답노트 | **서버 재시작 시 사라짐** | 계속 쌓임 |
| 비용 | 0원 | 0원 |

---

# A · 그냥 GitHub에 올리고 Streamlit으로 돌리기

## 1. 로컬에서 한 번 확인

```bash
pip install -r requirements.txt
python seed.py          # 시험지 4개를 DB에 적재
streamlit run app.py
```

## 2. GitHub에 올리기

```bash
git init
git add .
git commit -m "과외 자동채점 사이트"
git branch -M main
git remote add origin https://github.com/LongS1eeper/exam-app.git
git push -u origin main
```

`data/papers`(시험지·해설 이미지)는 **일부러 함께 올라갑니다.** 그래야 서버가 재시작해도
시험지가 자동으로 복구됩니다. `data/exam.db`(학생 성적)는 개인정보라 `.gitignore` 로 빠집니다.

저장소는 **Private** 으로 만드세요. Streamlit Cloud는 비공개 저장소도 연결됩니다.

## 3. Streamlit Cloud

1. <https://share.streamlit.io> → GitHub 로그인 → **New app**
2. Repository = 방금 만든 저장소 / Branch = `main` / Main file path = `app.py`
3. **Advanced settings → Secrets** (지금은 이 정도만)

   ```toml
   TEACHER_PIN = "선생님만 아는 비밀번호"
   APP_URL = "https://내앱주소.streamlit.app"
   ```

   알림(메일·텔레그램)은 배포 뒤 **앱 안에서** 설정하는 게 편합니다. 굳이 여기 넣으려면:

   ```toml
   MAIL_HOST = "smtp.naver.com"
   MAIL_PORT = "465"
   MAIL_USER = "내아이디@naver.com"
   MAIL_PASS = "앱 비밀번호"
   MAIL_TO   = "내아이디@naver.com"
   ```

4. **Deploy** → 2~3분 뒤 나오는 주소를 학생에게 알려 주면 끝입니다.

## 4. 알아 둘 것

**성적은 서버가 재시작하면 사라집니다.** Streamlit Cloud는 앱이 잠들 때 서버에 쓴 파일을
지웁니다. 시험지는 저장소에서 자동 복구되지만 학생 계정·점수·오답노트는 남지 않습니다.

그래도 **한 회차는 온전히 굴러갑니다** — 학생이 풀고, 채점받고, 해설을 보고,
선생님은 메일이나 텔레그램으로 결과를 받습니다. 사라지는 건 "지난달 대비 얼마나 늘었나" 같은 누적
기록뿐입니다. 누적이 필요해지면 아래 B를 10분만 하면 됩니다.

**앱이 잠듭니다.** 오래 안 쓰면 학생 첫 접속에서 "앱을 깨우는 중"이 20~30초 뜹니다.
수업 10분 전에 한 번 열어 두면 학생은 바로 들어옵니다.

## 5. 시험지가 계속 쌓이게 (토큰 3분)

이걸 켜지 않으면 앱에서 올린 시험지가 재시작 때 사라집니다. 켜면 앱이 저장소에
**자동으로 커밋**해서 계속 누적됩니다.

1. GitHub → Settings → Developer settings → Personal access tokens →
   **Fine-grained tokens** → *Generate new token*
2. Repository access = 이 앱 저장소 하나 / Permissions → **Contents: Read and write**
3. 앱 → 선생님 → 설정 → **GitHub 저장** 에 토큰과 `소유자/저장소` 를 넣고 **연결 테스트**

secrets 에 미리 넣어 둬도 됩니다.

```toml
GITHUB_TOKEN = "github_pat_..."
GITHUB_REPO = "LongS1eeper/exam-app"
GITHUB_BRANCH = "main"
```

앱이 커밋하면 Streamlit이 1~2분 뒤 자동으로 다시 뜹니다. 정상이니 놀라지 마시고,
**시험 중에는 시험지를 등록하지 마세요.**

터미널에서 직접 올리는 방법도 그대로 됩니다.

```bash
python ingest.py 새시험지.pdf --code Q3 --title "광성고 대비 3회"
git add data/papers && git commit -m "Q3 추가" && git push
```

---

# B · 성적을 계속 쌓고 싶어지면 (Neon 추가)

코드는 손대지 않습니다. **secrets 에 `DATABASE_URL` 한 줄만 늘어납니다.**

## 1. Neon 프로젝트

<https://neon.com> 가입 → **New Project** → 연결 주소 복사

```
postgresql://사용자:비밀번호@ep-xxxx.aws.neon.tech/neondb?sslmode=require
```

Supabase가 아니라 Neon인 이유: Supabase 무료는 7일간 활동이 없으면 프로젝트가 정지돼
매주 손으로 깨워야 합니다. Neon은 5분 놀면 잠들었다가 접속하면 1초 만에 깨어나고,
영구 정지가 없습니다.

## 2. 연결 확인 + 시험지 이전

```bash
DATABASE_URL="붙여넣은_주소" python dbcheck.py
DATABASE_URL="붙여넣은_주소" python seed.py
```

> Windows PowerShell이면 `$env:DATABASE_URL="주소"; python dbcheck.py`

`dbcheck.py` 는 접속·테이블 생성·이미지 저장·채점까지 실제로 해 보고 흔적을 지웁니다.
여기서 통과하면 나머지는 설정 문제뿐입니다.

## 3. Secrets 한 줄 추가

Streamlit Cloud → 앱 → Settings → Secrets 에 추가하고 저장하면 자동 재시작됩니다.

```toml
DATABASE_URL = "postgresql://...?sslmode=require"
```

이제 선생님 화면 **설정 → 저장 상태** 가 "외부 DB 모드"로 바뀝니다. 앱에서 PDF를 올려도
영구 저장되고, 원한다면 `.gitignore` 에서 `# data/papers/` 의 `#` 을 지워 저장소에서
시험지를 빼도 됩니다.

용량은 Neon 0.5GB 기준 시험지 약 30개. 더 필요하면 `ingest.py` 의 `dpi=150` 을 120으로
낮추면 절반 가까이 줄어듭니다.

---

## 문제가 생기면

| 증상 | 확인할 것 |
|---|---|
| 시험지가 하나도 없음 | `data/papers` 가 저장소에 올라갔는지 (A) / `seed.py` 를 돌렸는지 (B) |
| `psycopg2` 오류 | `requirements.txt` 가 저장소에 올라갔는지 |
| 알림이 안 옴 | 설정 화면의 **테스트 발송** 버튼을 누르면 실패 원인이 그대로 찍힙니다 |
| 접속이 느림 | 앱이 잠들었던 것. 두 번째부터는 빠릅니다 |
| 성적이 사라짐 | A 모드의 정상 동작입니다. B로 넘어가세요 |
| 시험지가 사라짐 | GitHub 저장이 꺼져 있던 것. 설정 → GitHub 저장 → 연결 테스트 |
| 앱이 자꾸 재시작 | 시험지를 저장소에 커밋할 때마다 일어납니다. 정상입니다 |
| 로컬로 되돌리고 싶음 | `DATABASE_URL` 없이 `streamlit run app.py` |

## 코드를 고쳤을 때

```bash
git add . && git commit -m "무엇을 고쳤는지" && git push
```

푸시하면 Streamlit Cloud가 알아서 다시 배포합니다.
