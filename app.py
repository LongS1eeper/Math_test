"""과외 시험 · 자동채점 사이트 (Streamlit)

실행:  streamlit run app.py
"""
from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="시험 · 자동채점", page_icon="📝", layout="wide")

# secrets → 환경변수 (core 가 DATABASE_URL 을 읽기 전에 넣어 준다)
for _k in ("DATABASE_URL", "TEACHER_PIN", "APP_URL",
           "GITHUB_TOKEN", "GITHUB_REPO", "GITHUB_BRANCH",
           "MAIL_TO", "MAIL_USER", "MAIL_PASS", "MAIL_HOST", "MAIL_PORT", "MAIL_FROM",
           "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
    try:
        if _k in st.secrets and not os.environ.get(_k):
            os.environ[_k] = str(st.secrets[_k])
    except Exception:
        pass

import core        # noqa: E402
import gitstore    # noqa: E402
import notify      # noqa: E402

CHOICE_LABEL = ["①", "②", "③", "④", "⑤"]

MOBILE_CSS = """
<style>
/* 본문 폭 — 카드 이미지가 과하게 늘어나지 않게 */
.block-container{max-width:1100px;}
img{max-width:100%;}
[data-testid="stImage"] img{max-width:820px;}

/* 선택지: 줄바꿈 허용 + 누르기 쉬운 크기 */
div[role="radiogroup"]{gap:.55rem 1.1rem; flex-wrap:wrap;}
div[role="radiogroup"] label{padding:6px 4px; font-size:1.05rem;}

/* 타이머를 위에 붙여 둔다 (iframe 은 카운트다운 하나뿐) */
div[data-testid="element-container"]:has(> iframe){
  position:sticky; top:0; z-index:99; background:var(--background-color,#fff);
  padding:4px 0;
}

@media (max-width:820px){
  .block-container{padding:1rem .8rem 4.5rem !important;}
  h1{font-size:1.75rem !important;}
  h2{font-size:1.5rem !important;}
  h3{font-size:1.3rem !important;}
  [data-testid="stImage"] img{max-width:100%;}
  /* 지표 3개가 한 줄에 들어가게 */
  [data-testid="stMetricValue"]{font-size:1.5rem !important;}
  [data-testid="stMetricLabel"]{font-size:.78rem !important;}
  div[role="radiogroup"]{gap:.5rem .8rem;}
  div[role="radiogroup"] label{padding:8px 6px;}
  /* 표가 옆으로 삐져나가지 않게 */
  [data-testid="stDataFrame"]{font-size:.85rem;}
}
</style>
"""


# ------------------------------------------------------------------ 공통
def ss(key, default=None):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]


def wide(fn, *args, **kw):
    try:
        return fn(*args, use_container_width=True, **kw)
    except TypeError:
        return fn(*args, width="stretch", **kw)


def img(data):
    wide(st.image, data)


def table(df):
    wide(st.dataframe, df, hide_index=True)


def box(height: int):
    """스크롤되는 영역. 구버전 streamlit 이면 그냥 컨테이너."""
    try:
        return st.container(height=height, border=False)
    except TypeError:
        return st.container()


@st.cache_resource
def boot():
    """앱이 처음 뜰 때 한 번 — DB가 비어 있으면 저장소의 시험지를 채운다."""
    return core.autoseed()


def sweep_expired():
    for a in core.db().query("SELECT * FROM attempts WHERE status='ongoing'"):
        if datetime.fromisoformat(a["deadline"]) <= datetime.now():
            res = core.grade_attempt(a["id"], auto=True)
            notify.notify_submission(res["attempt_id"])


def countdown_bar(title: str, deadline: datetime):
    """제목 + 남은 시간을 한 줄로. 스크롤해도 위에 붙어 있는다."""
    ms = int(deadline.timestamp() * 1000)
    safe = title.replace("<", "&lt;").replace(">", "&gt;")
    components.html(
        f"""
        <div style="font-family:-apple-system,system-ui,'Noto Sans KR',sans-serif;
             display:flex;align-items:center;justify-content:space-between;gap:10px;
             padding:9px 14px;border-radius:10px;background:#f2f4f8;color:#1f2937"
             id="bar">
          <span style="font-weight:600;font-size:15px;overflow:hidden;
                white-space:nowrap;text-overflow:ellipsis">{safe}</span>
          <span id="cd" style="font-weight:800;font-size:26px;
                font-variant-numeric:tabular-nums;flex:none">--:--</span>
        </div>
        <script>
        const end = {ms};
        function t() {{
          const s = Math.max(0, Math.floor((end - Date.now())/1000));
          const m = String(Math.floor(s/60)).padStart(2,'0');
          const q = String(s%60).padStart(2,'0');
          document.getElementById('cd').textContent = s>0 ? (m+':'+q) : '시간 종료';
          const bar = document.getElementById('bar');
          bar.style.background = s<=300 ? '#fee2e2' : '#f2f4f8';
          bar.style.color      = s<=300 ? '#b91c1c' : '#1f2937';
        }}
        t(); setInterval(t, 1000);
        </script>
        """,
        height=54,
    )


@st.cache_data(show_spinner=False, max_entries=1024)
def _imgs(code: str, kind: str, no: int, stamp: str):
    return core.images(code, kind, no)


@st.cache_data(show_spinner=False, max_entries=64)
def _pages(code: str, stamp: str):
    return core.page_images(code)


@st.cache_data(show_spinner=False, ttl=30)
def _stamp(code: str) -> str:
    r = core.db().one("SELECT updated_at FROM papers WHERE code=?", (code,))
    return r["updated_at"] if r else ""


def qimg(code: str, kind: str, no: int):
    """DB에서 이미지를 가져와 표시 (시험지가 갱신되면 캐시 자동 무효화)."""
    for data in _imgs(code, kind, no, _stamp(code)):
        img(data)


def pageimg(code: str):
    for data in _pages(code, _stamp(code)):
        img(data)


def show_answer(q):
    return CHOICE_LABEL[int(q["answer"]) - 1] if q["qtype"] == "choice" \
        and str(q["answer"]) in list("12345") else q["answer"]


# ------------------------------------------------------------------ 로그인
def login_view():
    st.title("📝 시험 · 자동채점")
    tab_s, tab_t = st.tabs(["학생", "선생님"])

    with tab_s:
        names = [r["name"] for r in core.db().query("SELECT name FROM students ORDER BY name")]
        mode = st.radio("접속", ["기존 학생", "처음 사용"], horizontal=True,
                        label_visibility="collapsed")
        if mode == "기존 학생" and names:
            name = st.selectbox("이름", names)
        else:
            name = st.text_input("이름")
        pin = st.text_input("비밀번호 4자리", type="password", max_chars=8)
        if wide(st.button, "들어가기", type="primary"):
            if not name or not pin:
                st.error("이름과 비밀번호를 입력하세요.")
            else:
                s = core.get_or_create_student(name, pin)
                if s is None:
                    st.error("비밀번호가 다릅니다.")
                else:
                    st.session_state.role = "student"
                    st.session_state.sid = s["id"]
                    st.session_state.sname = s["name"]
                    st.rerun()

    with tab_t:
        tpin = st.text_input("선생님 비밀번호", type="password")
        saved = os.environ.get("TEACHER_PIN", "") or core.setting("teacher_pin", "")
        if not saved:
            st.caption("처음 접속입니다. 입력한 값이 선생님 비밀번호로 저장됩니다.")
        if wide(st.button, "관리자 로그인"):
            if not saved and tpin:
                core.set_setting("teacher_pin", tpin)
                saved = tpin
            if tpin and tpin == saved:
                st.session_state.role = "teacher"
                st.rerun()
            else:
                st.error("비밀번호가 다릅니다.")


# ------------------------------------------------------------------ 학생 · 시험
def exam_view():
    sid = st.session_state.sid
    att = core.ongoing_attempt(sid)

    if att is None:
        st.subheader("시험 시작")
        papers = core.list_papers()
        if not papers:
            st.warning("등록된 시험지가 없습니다. 선생님께 문의하세요.")
            return
        labels = {f'{p["code"]} · {p["title"]} ({p["n_questions"]}문항 / {p["duration_min"]}분)': p
                  for p in papers}
        pick = st.selectbox("시험지", list(labels))
        p = labels[pick]
        done = core.db().one("SELECT COUNT(*) AS n FROM attempts WHERE student_id=? AND "
                             "paper_code=? AND status='done'", (sid, p["code"]))["n"]
        if done:
            st.info(f"이 시험지는 이미 {done}회 응시했습니다. 다시 보면 새 기록이 쌓입니다.")
        st.caption("화면에는 답안지(OMR)만 나옵니다. 종이 시험지를 보고 답만 표시하세요.")
        st.caption("시작을 누르면 타이머가 돌아가고, 시간이 끝나면 자동으로 제출·채점됩니다.")
        if st.button("▶ 시작하기", type="primary"):
            core.start_attempt(sid, p["code"], p["duration_min"])
            st.rerun()
        return

    # ---- 진행 중 ----
    meta, qs = core.load_paper(att["paper_code"])
    if (datetime.fromisoformat(att["deadline"]) - datetime.now()).total_seconds() <= 0:
        res = core.grade_attempt(att["id"], auto=True)
        notify.notify_submission(res["attempt_id"])
        st.session_state.auto_msg = True
        st.session_state.nav_to = "결과"
        st.rerun()

    countdown_bar(f'{meta["title"]} · {meta["n_questions"]}문항',
                  datetime.fromisoformat(att["deadline"]))

    resp = core.get_responses(att["id"])
    marked = 0

    st.caption("종이 시험지를 보고 답만 표시하세요. 표시하는 즉시 저장되고, "
               "창을 닫았다 다시 들어와도 남아 있습니다.")
    for q in qs:
        no = q["no"]
        cur = (resp.get(no) or {}).get("answer") or ""
        new_ans = answer_input(q, cur, f"ans_{att['id']}_{no}", label=f"{no}번")
        if new_ans != cur:
            core.save_response(att["id"], no, new_ans)
        if new_ans:
            marked += 1

    st.progress(marked / max(1, len(qs)), text=f"표시한 문항 {marked} / {len(qs)}")
    if marked < len(qs):
        st.warning(f"아직 표시하지 않은 문항 {len(qs) - marked}개가 있습니다. "
                   "무응답은 오답으로 처리됩니다.")
    st.divider()
    a, b = st.columns([1, 3])
    if wide(a.button, "제출하고 채점받기", type="primary"):
        res = core.grade_attempt(att["id"])
        notify.notify_submission(res["attempt_id"])
        st.session_state.nav_to = "결과"
        st.rerun()
    if b.button("시험 취소(기록 삭제)"):
        core.db().exec("DELETE FROM responses WHERE attempt_id=?", (att["id"],))
        core.db().exec("DELETE FROM attempts WHERE id=?", (att["id"],))
        st.rerun()


def answer_input(q, cur: str, key: str, label: str | None = None) -> str:
    vis = "visible" if label else "collapsed"
    text = label or key
    if q["qtype"] == "choice":
        idx = int(cur) - 1 if cur.isdigit() and 1 <= int(cur) <= 5 else None
        v = st.radio(text, CHOICE_LABEL, index=idx, horizontal=True, key=key,
                     label_visibility=vis)
        return str(CHOICE_LABEL.index(v) + 1) if v else ""
    hint = core.answer_hint(q)
    val = st.text_input(text, value=cur, key=key, label_visibility=vis,
                        placeholder=hint)
    st.caption(hint)
    return val


# ------------------------------------------------------------------ 학생 · 결과
def result_view():
    sid = st.session_state.sid
    if st.session_state.pop("auto_msg", False):
        st.warning("⏱ 시간이 종료되어 자동 제출·채점되었습니다.")
    rows = core.db().query("SELECT * FROM attempts WHERE student_id=? AND status='done' "
                           "ORDER BY id DESC", (sid,))
    if not rows:
        st.info("아직 채점된 시험이 없습니다.")
        return
    labels = {f'{r["paper_code"]} · {r["submitted_at"][:16].replace("T"," ")} · {r["score"]}점': r
              for r in rows}
    att = labels[st.selectbox("응시 기록", list(labels))]

    meta, qs = core.load_paper(att["paper_code"])
    resp = core.get_responses(att["id"])
    qmap = {q["no"]: q for q in qs}

    m1, m2, m3 = st.columns(3)
    m1.metric("점수", f'{att["score"]}점')
    m2.metric("맞은 개수", f'{int(att["score"]*att["total"]/100+0.5)} / {int(att["total"])}')
    pend = [n for n, r in resp.items() if r["is_correct"] is None]
    m3.metric("선생님 확인 대기", f"{len(pend)}문항")
    if att["auto_submitted"]:
        st.caption("⏱ 시간 종료로 자동 제출된 회차입니다.")

    st.markdown("#### 단원별 정답률")
    us = core.unit_stats(att["id"])
    if us:
        table(pd.DataFrame([{"단원": u, "정답": a, "문항": b, "정답률(%)": round(a / b * 100)}
                            for u, (a, b) in us.items()]))

    st.markdown("#### 문항별 결과")
    cells = ""
    for q in qs:
        r = resp.get(q["no"])
        v = r["is_correct"] if r else 0
        mark = "⭕" if v == 1 else ("🟡" if v is None else "❌")
        cells += (f'<div style="flex:0 0 auto;width:52px;text-align:center;'
                  f'padding:4px 0"><div style="font-size:.78rem;opacity:.65">'
                  f'{q["no"]}</div><div style="font-size:1.05rem">{mark}</div></div>')
    st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:2px 0">{cells}</div>',
                unsafe_allow_html=True)
    st.caption("⭕ 정답 · ❌ 오답 · 🟡 서술형(선생님 확인)")

    st.markdown("#### 틀린 문항 해설")
    wrong = [q["no"] for q in qs if resp.get(q["no"]) and resp[q["no"]]["is_correct"] == 0]
    if not wrong:
        st.success("틀린 문항이 없습니다.")
    for no in wrong:
        q = qmap[no]
        with st.expander(f'{no}번  ·  {q.get("unit","")}  ·  '
                         f'내 답 {resp[no]["answer"] or "무응답"} / 정답 {show_answer(q)}'):
            qimg(att["paper_code"], "q", no)
            st.markdown("**해설**")
            qimg(att["paper_code"], "a", no)

    with st.expander("맞은 문항 해설도 보기"):
        pick = st.selectbox("문항 번호", [q["no"] for q in qs], key="allsol")
        qimg(att["paper_code"], "a", pick)


# ------------------------------------------------------------------ 학생 · 오답노트
def wrongnote_view():
    sid = st.session_state.sid
    show_all = st.toggle("해결한 문항도 보기")
    notes = core.wrong_notes(sid, only_open=not show_all)
    if not notes:
        st.success("오답노트가 비어 있습니다.")
        return

    units = {}
    for n in notes:
        units.setdefault(n["unit"] or "미분류", []).append(n)
    st.markdown("#### 유형별 오답 수")
    table(pd.DataFrame([{"단원": u, "오답 수": len(v)} for u, v in units.items()]))

    for u, items in units.items():
        st.markdown(f"### {u}")
        for n in items:
            meta, qs = core.load_paper(n["paper_code"])
            q = next(x for x in qs if x["no"] == n["no"])
            solved = "✅ " if n["resolved_at"] else ""
            with st.expander(f'{solved}{n["paper_code"]} {n["no"]}번  '
                             f'(다시 푼 횟수 {n["retry_count"]})'):
                qimg(n["paper_code"], "q", n["no"])
                given = answer_input(q, "", f'retry_{n["id"]}')
                cc1, cc2 = st.columns(2)
                if cc1.button("채점", key=f'g{n["id"]}'):
                    ok = core.judge(q, given)
                    core.db().exec(
                        "UPDATE wrongnotes SET retry_count=retry_count+1 WHERE id=?", (n["id"],))
                    if ok == 1:
                        core.db().exec("UPDATE wrongnotes SET resolved_at=? WHERE id=?",
                                       (core.now(), n["id"]))
                        st.success("정답입니다. 오답노트에서 해결 처리했습니다.")
                    elif ok == 0:
                        st.error(f"아직 오답입니다. 정답은 {show_answer(q)}")
                    else:
                        st.info("서술형은 선생님이 확인합니다.")
                if cc2.button("해설 보기", key=f's{n["id"]}'):
                    qimg(n["paper_code"], "a", n["no"])


# ------------------------------------------------------------------ 학생 · 성적 추이
def trend_view():
    sid = st.session_state.sid
    rows = core.db().query("SELECT paper_code, submitted_at, score FROM attempts "
                           "WHERE student_id=? AND status='done' ORDER BY id", (sid,))
    if not rows:
        st.info("기록이 없습니다.")
        return
    df = pd.DataFrame([{"응시": r["submitted_at"][:16].replace("T", " "),
                        "시험지": r["paper_code"], "점수": r["score"]} for r in rows])
    st.line_chart(df.set_index("응시")["점수"])
    table(df)


# ------------------------------------------------------------------ 선생님
def teacher_dashboard():
    st.subheader("제출 현황")
    rows = core.db().query(
        "SELECT a.*, s.name FROM attempts a JOIN students s ON s.id=a.student_id "
        "WHERE a.status='done' ORDER BY a.id DESC LIMIT 50")
    new = [r for r in rows if not r["teacher_seen"]]
    if new:
        st.warning(f"🔔 확인하지 않은 제출 {len(new)}건")
    if not rows:
        st.info("제출 기록이 없습니다.")
        return
    table(pd.DataFrame([{
        "확인": "🔔" if not r["teacher_seen"] else "",
        "알림": "✈️" if r.get("notified") else "",
        "학생": r["name"], "시험지": r["paper_code"],
        "제출": r["submitted_at"][:16].replace("T", " "),
        "점수": r["score"], "자동제출": "예" if r["auto_submitted"] else ""} for r in rows]))
    if st.button("모두 확인 처리"):
        core.db().exec("UPDATE attempts SET teacher_seen=1 WHERE status='done'")
        st.rerun()

    st.divider()
    st.subheader("학생별 취약 유형")
    rows = core.db().query(
        "SELECT s.name AS name, w.unit AS unit, COUNT(*) AS n FROM wrongnotes w "
        "JOIN students s ON s.id=w.student_id WHERE w.resolved_at IS NULL "
        "GROUP BY s.name, w.unit ORDER BY n DESC")
    if rows:
        table(pd.DataFrame([{"학생": r["name"], "단원": r["unit"], "미해결 오답": r["n"]}
                            for r in rows]))


def _after_paper_change(code: str, action: str = "저장"):
    """시험지가 바뀌면 저장소에도 반영한다."""
    if not gitstore.configured():
        if core.db().pg:
            st.caption("외부 DB에 저장되었습니다. 서버가 재시작해도 그대로 남습니다.")
        else:
            st.info("이 시험지는 서버가 재시작되면 사라집니다. 외부 DB(DATABASE_URL)를 "
                    "쓰거나, 설정 → GitHub 저장 을 켜 두면 계속 쌓입니다.")
        return
    with st.spinner("저장소에 올리는 중..."):
        ok, msg = (gitstore.delete_paper(code) if action == "삭제"
                   else gitstore.push_paper(code))
    if ok:
        st.success(f"저장소 {msg}")
        st.caption("저장소가 바뀌었으니 Streamlit이 1~2분 뒤 앱을 자동으로 다시 띄웁니다. "
                   "그동안 잠깐 느려질 수 있습니다.")
    else:
        st.error(f"저장소 반영 실패 — {msg}")


def teacher_papers():
    st.subheader("시험지 등록")
    st.caption("문제 + [정답 및 해설]이 한 파일에 있는 PDF를 올리면 문항·정답·해설을 자동으로 "
               "뜯어 냅니다.")
    if gitstore.configured():
        st.caption(f"등록하면 `{gitstore.repo()}` 저장소에도 자동으로 올라가 계속 쌓입니다.")

    up = st.file_uploader("시험지 PDF", type="pdf")
    c1, c2, c3 = st.columns(3)
    code = c1.text_input("코드 (영문·숫자)", placeholder="Q3")
    title = c2.text_input("제목", placeholder="광성고 대비 3회")
    dur = c3.number_input("제한시간(분)", 10, 180, 50)
    if st.button("등록하고 자동 분석", type="primary") and up and code and title:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / f"{code}.pdf"
            path.write_bytes(up.getbuffer())
            with st.spinner("PDF 분석 중 (문항·정답·해설 추출)..."):
                try:
                    import ingest
                    meta = ingest.ingest(path, code.strip(), title.strip(),
                                         int(dur), quiet=True)
                except Exception as e:
                    st.error(f"분석 실패: {type(e).__name__}: {e}")
                    return
        need = meta.get("needs_check") or []
        st.success(f'{meta["n_questions"]}문항 등록 완료.' +
                   (f' 주관식 {len(need)}문항({need})의 정답을 아래에서 채워 주세요.'
                    if need else ''))
        if not need:
            _after_paper_change(code.strip())
        else:
            st.info("주관식 정답을 채우고 **정답표 저장**을 누르면 그때 저장소에 올립니다.")

    st.divider()
    st.subheader("정답표 확인 · 수정")
    papers = core.list_papers()
    if not papers:
        return
    pick = st.selectbox("시험지", [p["code"] for p in papers])
    meta, qs = core.load_paper(pick)
    need = [q["no"] for q in qs if q["needs_check"]]
    if need:
        st.warning(f"자동 추출이 안 된 문항: {need} — 정답을 채워 주세요.")

    with st.expander("시험지 전체 보기 (인쇄용)"):
        st.caption("학생에게 나눠 줄 시험지입니다. 브라우저 인쇄(Ctrl+P)로 출력하세요.")
        pageimg(pick)

    with st.expander("해설 이미지로 정답 확인하기"):
        n = st.selectbox("문항", [q["no"] for q in qs], key="chk")
        qimg(pick, "a", n)

    df = pd.DataFrame(qs)[["no", "qtype", "answer", "unit", "needs_check"]]
    edited = wide(
        st.data_editor, df, hide_index=True, num_rows="fixed",
        column_config={
            "no": st.column_config.NumberColumn("번호", disabled=True),
            "qtype": st.column_config.SelectboxColumn(
                "유형", options=["choice", "short", "essay"]),
            "answer": st.column_config.TextColumn("정답 (객관식은 1~5)"),
            "unit": st.column_config.TextColumn("단원"),
            "needs_check": st.column_config.CheckboxColumn("확인필요"),
        })
    b1, b2, b3 = st.columns([1, 1, 2])
    if b1.button("정답표 저장", type="primary"):
        m = {int(r["no"]): r for _, r in edited.iterrows()}
        for q in qs:
            r = m[q["no"]]
            q.update(qtype=r["qtype"], answer=str(r["answer"]),
                     unit=r["unit"], needs_check=bool(r["needs_check"]))
        core.save_answers(pick, qs)
        st.success("저장했습니다.")
        _after_paper_change(pick)
    if b2.button("저장소에 올리기", disabled=not gitstore.configured()):
        _after_paper_change(pick)
    if b3.button(f"{pick} 시험지 삭제"):
        core.delete_paper(pick)
        _after_paper_change(pick, "삭제")
        st.rerun()

    st.divider()
    st.subheader("저장소 동기화")
    if not gitstore.configured():
        st.info("설정 → **GitHub 저장** 을 켜면 시험지가 저장소에 쌓여서 "
                "서버가 재시작해도 그대로 남습니다.")
        return
    rows, err = gitstore.status()
    if err:
        st.error(err)
        return
    table(pd.DataFrame(rows))
    missing = [r["시험지"] for r in rows if r["상태"] == "저장 안 됨"]
    if missing:
        st.warning(f"저장소에 아직 없는 시험지: {', '.join(missing)}")
    if st.button("앱에 있는 시험지 전부 저장소로"):
        with st.spinner("올리는 중..."):
            ok, msgs = gitstore.push_all()
        st.success(f"{ok}개 완료")
        st.code("\n".join(msgs))


def teacher_essay():
    st.subheader("서술형 채점")
    rows = core.db().query(
        "SELECT r.attempt_id AS attempt_id, r.no AS no, r.answer AS answer, "
        "a.paper_code AS paper_code, s.name AS name "
        "FROM responses r JOIN attempts a ON a.id=r.attempt_id "
        "JOIN students s ON s.id=a.student_id "
        "WHERE r.is_correct IS NULL AND a.status='done' ORDER BY r.attempt_id, r.no")
    if not rows:
        st.success("채점할 서술형이 없습니다.")
        return
    for r in rows:
        meta, qs = core.load_paper(r["paper_code"])
        q = next(x for x in qs if x["no"] == r["no"])
        with st.expander(f'{r["name"]} · {r["paper_code"]} {r["no"]}번'):
            st.write("**학생 답안**")
            st.code(r["answer"] or "(무응답)")
            st.write("**정답**")
            st.code(q["answer"])
            qimg(r["paper_code"], "a", r["no"])
            a, b = st.columns(2)
            if a.button("정답 처리", key=f'ok{r["attempt_id"]}_{r["no"]}'):
                _mark_essay(r, 1)
                st.rerun()
            if b.button("오답 처리", key=f'ng{r["attempt_id"]}_{r["no"]}'):
                _mark_essay(r, 0)
                st.rerun()


def _mark_essay(r, val: int):
    d = core.db()
    d.exec("UPDATE responses SET is_correct=? WHERE attempt_id=? AND no=?",
           (val, r["attempt_id"], r["no"]))
    att = d.one("SELECT * FROM attempts WHERE id=?", (r["attempt_id"],))
    if val == 0:
        _, qs = core.load_paper(att["paper_code"])
        q = next(x for x in qs if x["no"] == r["no"])
        d.exec("INSERT INTO wrongnotes(student_id,paper_code,no,unit,created_at) "
               "VALUES(?,?,?,?,?) ON CONFLICT(student_id,paper_code,no) "
               "DO UPDATE SET resolved_at=NULL",
               (att["student_id"], att["paper_code"], r["no"], q.get("unit") or "", core.now()))
    rs = d.query("SELECT is_correct FROM responses WHERE attempt_id=? "
                 "AND is_correct IS NOT NULL", (r["attempt_id"],))
    g = len(rs)
    ok = sum(x["is_correct"] for x in rs)
    d.exec("UPDATE attempts SET score=?, total=? WHERE id=?",
           (round(ok / g * 100, 1) if g else 0, g, r["attempt_id"]))


def teacher_students():
    st.subheader("학생")
    rows = core.db().query(
        "SELECT s.id AS id, s.name AS name, COUNT(a.id) AS n, AVG(a.score) AS avg "
        "FROM students s LEFT JOIN attempts a ON a.student_id=s.id AND a.status='done' "
        "GROUP BY s.id, s.name ORDER BY s.name")
    table(pd.DataFrame([{"이름": r["name"], "응시 횟수": r["n"],
                         "평균": round(r["avg"], 1) if r["avg"] is not None else None}
                        for r in rows]))
    d = st.selectbox("삭제할 학생", ["-"] + [r["name"] for r in rows])
    if d != "-" and st.button("삭제 (기록 포함)"):
        sid = next(r["id"] for r in rows if r["name"] == d)
        db = core.db()
        db.exec("DELETE FROM responses WHERE attempt_id IN "
                "(SELECT id FROM attempts WHERE student_id=?)", (sid,))
        db.exec("DELETE FROM attempts WHERE student_id=?", (sid,))
        db.exec("DELETE FROM wrongnotes WHERE student_id=?", (sid,))
        db.exec("DELETE FROM students WHERE id=?", (sid,))
        st.rerun()


TEST_SUBJECT = "[채점] 연결 테스트"
TEST_BODY = ("연결 테스트입니다.\n"
             "이 메시지가 보이면 학생이 시험을 제출할 때마다 점수와 틀린 문항이 여기로 옵니다.")


def teacher_settings():
    st.subheader("제출 알림")
    ch = notify.channels()
    if ch:
        st.success("현재 **" + " · ".join(ch) + "** 로 알림이 갑니다.")
    else:
        st.warning("알림이 꺼져 있습니다. 아래에서 받을 곳을 지정하세요. "
                   "설정하지 않아도 채점은 정상 동작하고, 선생님 대시보드에 🔔로 표시됩니다.")

    url = st.text_input("앱 주소 (알림 끝에 링크로 붙습니다)",
                        value=os.environ.get("APP_URL", "") or core.setting("app_url", ""),
                        placeholder="https://내앱주소.streamlit.app")
    if st.button("앱 주소 저장"):
        core.set_setting("app_url", url.strip())
        st.success("저장했습니다.")

    tab_tg, tab_mail, tab_git = st.tabs(["텔레그램", "메일", "GitHub 저장"])

    # ---------------- 텔레그램 ----------------
    with tab_tg:
        st.caption("텔레그램에서 @BotFather 에게 /newbot 을 보내면 선생님 전용 봇과 "
                   "토큰이 생깁니다. 알림은 그 봇과의 1:1 채팅방으로 옵니다. "
                   "학생은 이 봇을 모릅니다.")
        tok = st.text_input("봇 토큰", value=core.setting("telegram_bot_token", ""),
                            type="password", placeholder="123456:AAE...")
        chat = st.text_input("chat id", value=core.setting("telegram_chat_id", ""))

        t1, t2, t3 = st.columns(3)
        if t1.button("저장", key="tg_save"):
            core.set_setting("telegram_bot_token", tok.strip())
            core.set_setting("telegram_chat_id", chat.strip())
            st.success("저장했습니다.")
            st.rerun()
        if t2.button("내 chat id 찾기", key="tg_find"):
            core.set_setting("telegram_bot_token", tok.strip())
            ids, msg = notify.find_chat_ids()
            st.info(msg)
            if ids:
                table(pd.DataFrame(ids))
        if t3.button("테스트 발송", key="tg_test"):
            core.set_setting("telegram_bot_token", tok.strip())
            core.set_setting("telegram_chat_id", chat.strip())
            ok, msg = notify.send_telegram(f"{TEST_SUBJECT}\n\n{TEST_BODY}")
            (st.success if ok else st.error)(msg)

    # ---------------- 메일 ----------------
    with tab_mail:
        st.caption("텔레그램 대신, 또는 함께 쓸 수 있습니다. 쓰시던 메일 계정으로 보냅니다.")
        names = list(notify.PRESETS)
        saved_host = core.setting("mail_host", "")
        cur = next((n for n in names if notify.PRESETS[n]["host"] == saved_host), names[0])
        provider = st.selectbox("메일 제공자", names, index=names.index(cur))
        st.info(notify.SETUP_HELP[provider])

        preset = notify.PRESETS[provider]
        c1, c2 = st.columns([2, 1])
        host = c1.text_input("SMTP 주소", value=preset["host"] or saved_host,
                             disabled=provider != "직접 입력")
        port = c2.text_input("포트", value=core.setting("mail_port", "") or preset["port"],
                             disabled=provider != "직접 입력")
        user = st.text_input("보내는 계정 (메일 주소)",
                             value=core.setting("mail_user", ""),
                             placeholder="dlwjdgh0423@naver.com")
        pw = st.text_input("비밀번호 (2단계 인증이면 앱 비밀번호)", type="password",
                           value=core.setting("mail_pass", ""))
        to = st.text_input("받을 주소", value=core.setting("mail_to", "") or user,
                           help="보내는 계정과 같아도 됩니다. 나에게 보내는 셈입니다.")

        def _save_mail():
            core.set_setting("mail_host", host.strip())
            core.set_setting("mail_port", port.strip() or "465")
            core.set_setting("mail_user", user.strip())
            core.set_setting("mail_pass", pw.strip())
            core.set_setting("mail_to", (to or user).strip())

        m1, m2, m3 = st.columns(3)
        if m1.button("저장", key="mail_save"):
            _save_mail()
            st.success("저장했습니다.")
            st.rerun()
        if m2.button("테스트 메일 보내기", key="mail_test", type="primary"):
            _save_mail()
            with st.spinner("보내는 중..."):
                ok, msg = notify.send_email(TEST_SUBJECT, TEST_BODY)
            (st.success if ok else st.error)(msg)
        if m3.button("메일 알림 끄기", key="mail_off"):
            for k in ("mail_host", "mail_user", "mail_pass", "mail_to"):
                core.set_setting(k, "")
            st.rerun()

    # ---------------- GitHub 저장 ----------------
    with tab_git:
        if core.db().pg:
            st.warning("**외부 DB를 쓰고 계셔서 이 기능은 필요 없습니다.** 시험지는 이미 DB에 "
                       "영구 저장됩니다. 저장소가 공개(Public)라면 **켜지 마세요** — "
                       "시험지·해설 이미지가 저장소에 커밋됩니다.")
        st.caption("등록한 시험지를 GitHub 저장소에 `data/papers/<코드>.zip` 으로 커밋합니다. "
                   "외부 DB 없이 Streamlit Cloud만 쓸 때 시험지를 살려 두는 용도입니다.")
        with st.expander("토큰 만드는 법", expanded=not gitstore.configured()):
            st.markdown(
                "1. GitHub → 우측 상단 프로필 → **Settings** → 맨 아래 "
                "**Developer settings** → **Personal access tokens** → "
                "**Fine-grained tokens** → *Generate new token*\n"
                "2. **Repository access** 에서 이 앱 저장소 하나만 고르기\n"
                "3. **Permissions → Repository permissions → Contents** 를 "
                "**Read and write** 로\n"
                "4. 만들면 한 번만 보이는 토큰을 복사해서 아래에 붙여넣기\n\n"
                "토큰은 이 앱의 DB에만 저장됩니다. Streamlit secrets 에 "
                "`GITHUB_TOKEN` 으로 넣어 두면 더 안전합니다.")
        gtok = st.text_input("토큰", value=core.setting("github_token", ""),
                             type="password", placeholder="github_pat_...")
        grepo = st.text_input("저장소", value=core.setting("github_repo", ""),
                              placeholder="LongS1eeper/exam-app")
        gbr = st.text_input("브랜치", value=core.setting("github_branch", "") or "main")

        g1, g2, g3 = st.columns(3)
        if g1.button("저장", key="git_save"):
            core.set_setting("github_token", gtok.strip())
            core.set_setting("github_repo", grepo.strip())
            core.set_setting("github_branch", gbr.strip() or "main")
            st.success("저장했습니다.")
            st.rerun()
        if g2.button("연결 테스트", key="git_test", type="primary"):
            core.set_setting("github_token", gtok.strip())
            core.set_setting("github_repo", grepo.strip())
            core.set_setting("github_branch", gbr.strip() or "main")
            with st.spinner("확인 중..."):
                ok, msg = gitstore.check()
            (st.success if ok else st.error)(msg)
        if g3.button("끄기", key="git_off"):
            for k in ("github_token", "github_repo"):
                core.set_setting(k, "")
            st.rerun()

        if gitstore.configured():
            st.caption("시험지·정답 화면 아래쪽 **저장소 동기화** 에서 "
                       "앱과 저장소의 상태를 비교하고 한꺼번에 올릴 수 있습니다.")

    if any(os.environ.get(k) for k in
           ("MAIL_USER", "MAIL_PASS", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
            "GITHUB_TOKEN", "GITHUB_REPO")):
        st.caption("secrets 또는 환경변수에 값이 있으면 여기서 입력한 값보다 우선합니다.")

    st.divider()
    st.subheader("저장 상태")
    n_papers = len(core.list_papers())
    n_students = core.db().one("SELECT COUNT(*) AS n FROM students")["n"]
    if core.db().pg:
        st.success(f"**외부 DB 모드** · {core.db().kind} — 서버가 재시작해도 "
                   "시험지·성적·오답노트가 그대로 남습니다.")
    else:
        st.info("**파일 모드** · 로컬 SQLite (`data/exam.db`)\n\n"
                "시험지는 저장소의 `data/papers` 에서 자동 복구되지만, "
                "**성적과 오답노트는 서버가 재시작되면 사라집니다.** "
                "누적해서 보시려면 secrets 에 `DATABASE_URL` 한 줄만 넣으면 "
                "코드 수정 없이 외부 DB로 바뀝니다. (DEPLOY.md 참고)")
    st.write(f"등록된 시험지 {n_papers}개 · 학생 {n_students}명")

    st.divider()
    st.subheader("선생님 비밀번호 변경")
    np1 = st.text_input("새 비밀번호", type="password", key="np1")
    if st.button("변경") and np1:
        core.set_setting("teacher_pin", np1)
        st.success("변경했습니다. (secrets 의 TEACHER_PIN 이 있으면 그 값이 우선합니다)")


# ------------------------------------------------------------------ main
def main():
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)
    ss("role")
    boot()
    sweep_expired()
    if st.session_state.role is None:
        login_view()
        return

    if "nav_to" in st.session_state:
        st.session_state["stud_menu"] = st.session_state.pop("nav_to")

    with st.sidebar:
        if st.session_state.role == "student":
            st.markdown(f"### {st.session_state.sname} 학생")
            page = st.radio("메뉴", ["시험 보기", "결과", "오답노트", "성적 추이"],
                            key="stud_menu")
        else:
            st.markdown("### 선생님")
            page = st.radio("메뉴", ["대시보드", "시험지·정답", "서술형 채점", "학생", "설정"])
        if st.button("로그아웃"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    if st.session_state.role == "student":
        {"시험 보기": exam_view, "결과": result_view,
         "오답노트": wrongnote_view, "성적 추이": trend_view}[page]()
    else:
        {"대시보드": teacher_dashboard, "시험지·정답": teacher_papers,
         "서술형 채점": teacher_essay, "학생": teacher_students,
         "설정": teacher_settings}[page]()


main()
