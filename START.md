# 여기부터 시작하세요

전부 무료이고, 처음부터 끝까지 **25분** 정도 걸립니다.
순서대로만 하시면 됩니다. 각 단계 끝에 **"이게 보이면 성공"** 을 적어 뒀습니다.

| 단계 | 하는 일 | 시간 |
|---|---|---|
| 1 | 내 PC에서 돌려 보기 | 5분 |
| 2 | 텔레그램 봇 만들기 | 5분 |
| 3 | GitHub에 올리기 | 5분 |
| 4 | 인터넷에 배포 | 7분 |
| 5 | 시험지 누적 켜기 | 3분 |
| 6 | 학생에게 주기 | — |

---

## 준비물

* **파이썬 3.10 이상.** 터미널(맥) 또는 명령 프롬프트/PowerShell(윈도우)에서 확인하세요.

  ```bash
  python --version
  ```

  안 깔려 있으면 <https://www.python.org/downloads/> 에서 설치합니다.
  윈도우는 설치 화면에서 **"Add python.exe to PATH"** 를 꼭 체크하세요.

* **GitHub 계정** (이미 있으시죠 — `LongS1eeper`)
* **텔레그램** 앱 (폰에 설치)

---

# 1단계 · 내 PC에서 돌려 보기 (5분)

압축을 풀고, 그 폴더에서 터미널을 엽니다.
(윈도우: 폴더 주소창에 `cmd` 입력 후 엔터 / 맥: 폴더에서 우클릭 → 터미널 열기)

```bash
pip install -r requirements.txt
python seed.py
streamlit run app.py
```

`seed.py` 는 시험지 4개(Q1·Q2·Q11·Q12, 132문항)를 데이터베이스에 넣습니다.
`streamlit run` 하면 브라우저가 저절로 열립니다.

**해 보세요**

1. **선생님** 탭 → 아무 비밀번호나 입력 → *관리자 로그인*
   (처음 입력한 값이 선생님 비밀번호로 저장됩니다)
2. 왼쪽 메뉴 → **시험지·정답** → 시험지 4개가 다 보이는지 확인
3. 로그아웃 → **학생** 탭 → *처음 사용* → 이름 `테스트` / 비밀번호 `1111`
4. Q1을 골라 **시작하기** → 몇 문항 답 찍고 → **제출하고 채점받기**
5. 점수·틀린 문항·해설이 나오는지 확인

> ✅ **이게 보이면 성공**: 채점 결과 화면에 점수와 ⭕❌ 격자가 뜬다.

> 잘 안 되면
> * `pip: command not found` → `python -m pip install -r requirements.txt`
> * `streamlit: command not found` → `python -m streamlit run app.py`
> * 그래도 막히면 화면에 뜨는 빨간 에러 메시지를 그대로 알려 주세요.

---

# 2단계 · 텔레그램 봇 만들기 (5분)

알림은 **선생님 전용 봇과의 1:1 채팅방**으로 옵니다. 학생은 이 봇을 모릅니다.

1. 텔레그램에서 **@BotFather** 를 검색해 대화 시작
2. `/newbot` 전송 → 봇 이름과 아이디를 정하라고 합니다 (아이디는 `_bot` 으로 끝나야 함)
3. **토큰**이 나옵니다. `123456789:AAE...` 이렇게 생긴 긴 문자열 — 복사해 두세요
4. 방금 만든 봇을 검색해 들어가서 **아무 메시지나 한 번 보냅니다** (`안녕` 이라고 쳐도 됨)
   → 이걸 해야 봇이 나에게 말을 걸 수 있습니다
5. 아직 켜져 있는 앱에서 → 선생님 → **설정** → **텔레그램** 탭
6. 토큰 붙여넣기 → **내 chat id 찾기** → 나온 숫자를 chat id 칸에 입력
7. **테스트 발송** → 폰에 메시지가 오는지 확인 → **저장**

> ✅ **이게 보이면 성공**: 폰 텔레그램에 `[채점] 연결 테스트` 메시지가 도착한다.

**토큰과 chat id 두 개를 메모해 두세요.** 4단계에서 다시 씁니다.

---

# 3단계 · GitHub에 올리기 (5분)

1. <https://github.com/new> → 저장소 이름 `exam-app` → **Private** 선택 → *Create repository*
2. 압축 푼 폴더에서 터미널을 열고 (1단계와 같은 폴더)

```bash
git init
git add .
git status
```

`git status` 결과에 **`data/exam.db` 가 없어야 합니다.** 학생 이름과 비밀번호가 든 파일이라
일부러 빼 두었습니다. `data/papers` 는 있어야 정상입니다 — 시험지가 여기 들어 있습니다.

```bash
git commit -m "과외 자동채점 사이트"
git branch -M main
git remote add origin https://github.com/LongS1eeper/exam-app.git
git push -u origin main
```

비밀번호를 물으면 GitHub 로그인 비밀번호가 아니라 **토큰**을 넣어야 합니다.
(<https://github.com/settings/tokens> → Tokens (classic) → Generate → `repo` 체크)

> ✅ **이게 보이면 성공**: GitHub 저장소 페이지에 `app.py` 와 `data/papers` 폴더가 보인다.

---

# 4단계 · 인터넷에 배포 (7분)

1. <https://share.streamlit.io> → **Sign in with GitHub**
2. **Create app** → *Deploy a public app from GitHub*
3. Repository `LongS1eeper/exam-app` / Branch `main` / Main file path `app.py`
4. **Advanced settings** → **Secrets** 칸에 아래를 붙여넣습니다
   (따옴표 안의 값만 바꾸세요)

   ```toml
   TEACHER_PIN = "선생님만 아는 비밀번호"
   TELEGRAM_BOT_TOKEN = "2단계에서 받은 토큰"
   TELEGRAM_CHAT_ID = "2단계에서 찾은 숫자"
   ```

5. **Deploy** → 2~3분 기다리면 주소가 나옵니다
   (`https://무언가.streamlit.app`)
6. 주소가 정해졌으니 Secrets에 한 줄 더 추가합니다 (앱 → Settings → Secrets)

   ```toml
   APP_URL = "https://받은주소.streamlit.app"
   ```

> ✅ **이게 보이면 성공**: 폰 브라우저로 그 주소를 열었을 때 로그인 화면이 뜬다.

---

# 5단계 · 시험지 누적 켜기 (3분)

이걸 안 하면 **앱에서 새로 올린 시험지가 서버 재시작 때 사라집니다.**
켜면 앱이 GitHub에 자동으로 저장해서 계속 쌓입니다.

1. GitHub → 우측 상단 프로필 → **Settings** → 맨 아래 **Developer settings**
2. **Personal access tokens** → **Fine-grained tokens** → *Generate new token*
3. 설정
   * Repository access → **Only select repositories** → `exam-app` 만 선택
   * Permissions → Repository permissions → **Contents** 를 **Read and write** 로
4. 만들면 토큰이 **한 번만** 보입니다. 복사하세요 (`github_pat_...`)
5. 배포된 앱 → 선생님 → 설정 → **GitHub 저장** 탭
   * 토큰 붙여넣기
   * 저장소 `LongS1eeper/exam-app`
   * **연결 테스트** → 초록색 메시지가 뜨면 **저장**

> ✅ **이게 보이면 성공**: `LongS1eeper/exam-app (비공개) · 브랜치 main · 쓰기 권한 OK`

이제 시험지·정답 화면에서 PDF를 올리면 저장소에 자동으로 커밋됩니다.
커밋될 때마다 Streamlit이 1~2분 뒤 앱을 다시 띄웁니다. 정상이니 놀라지 마시고,
**시험 중에는 시험지를 등록하지 마세요.**

---

# 6단계 · 학생에게 주기

학생에게는 **주소만** 알려 주면 됩니다. 나머지는 학생이 알아서 합니다.

> 이 주소로 들어가서 **학생** 탭 → *처음 사용* → 이름이랑 비밀번호 4자리 정해서 들어와.
> 다음부터는 그 이름이랑 비밀번호로 들어오면 돼.
> https://받은주소.streamlit.app

**첫 수업 전에**

* [ ] 수업 10분 전에 선생님이 앱을 한 번 열어 두기
      (오래 안 쓰면 잠들어서, 학생 첫 접속에 20~30초 걸립니다)
* [ ] 학생 폰으로 직접 한 번 열어 보기 — 글씨 크기가 괜찮은지
* [ ] 시험지를 종이로 뽑아 줄 거면 `시험지 전체 보기 (인쇄용)` 에서 출력

**첫 수업 끝나고 확인할 것 세 가지**

1. 주관식 입력이 학생에게 불편하지 않았는지 (`2√7` 같은 답)
2. 한 화면에 6문항이 적당한지 — 많으면 `app.py` 의 `PAGE_SIZE` 를 4로
3. 오답노트의 단원 분류가 선생님 판단과 맞는지

---

# 알아 두실 것 두 가지

**성적은 서버가 재시작하면 사라집니다.** Streamlit Cloud가 앱을 잠재울 때 서버 파일을
지우기 때문입니다. 시험지는 5단계 덕분에 살아남지만, 학생 계정·점수·오답노트는 남지 않습니다.

한 회차는 온전히 굴러갑니다 — 학생이 풀고, 채점받고, 해설을 보고, 선생님은 텔레그램으로
결과를 받습니다. 사라지는 건 "지난달보다 얼마나 늘었나" 같은 누적 기록뿐입니다.
그게 필요해지면 `DEPLOY.md` 의 **B안(Neon)** 을 10분만 하면 되고, 코드는 손대지 않습니다.

**저장소는 비공개로 두세요.** 시험지와 해설 이미지가 함께 올라가 있습니다.

---

# 막혔을 때

| 증상 | 확인할 것 |
|---|---|
| 앱은 뜨는데 시험지가 없음 | `data/papers` 가 GitHub에 올라갔는지 |
| 텔레그램이 안 옴 | 설정 → 텔레그램 → **테스트 발송** 을 누르면 실패 원인이 그대로 찍힙니다 |
| GitHub 저장 실패 | 401=토큰 / 404=저장소 이름 / 403=권한. **연결 테스트** 메시지에 나옵니다 |
| 학생 접속이 느림 | 앱이 잠들었던 것. 두 번째부터는 빠릅니다 |
| 새 시험지가 사라짐 | 5단계를 안 했거나 연결이 끊긴 것 |

더 자세한 설명

* `README.md` — 앱 사용법, 채점 규칙, 시험지 추가
* `DEPLOY.md` — 배포 상세, Neon 붙이기
* `screens/` — 학생이 보는 화면 예시 이미지

점검 명령 (내 PC에서)

```bash
python test_core.py        # DB·채점·알림 (132문항 정답표 전수 점검)
python test_mathcmp.py     # 채점 규칙 86가지
```
