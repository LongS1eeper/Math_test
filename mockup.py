"""학생 화면 예시 이미지를 만든다.

app.py 가 그리는 화면을 Streamlit 기본 테마 그대로 재현해 PNG 로 저장한다.
문제·해설은 DB 에 들어 있는 진짜 Q1 이미지를 쓴다.

    python mockup.py            →  mockups/*.png
"""
from __future__ import annotations

import base64
from pathlib import Path

import core

OUT = Path(__file__).parent / "mockups"
URL = "내앱주소.streamlit.app"

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{
  font-family:"Source Sans Pro","Noto Sans CJK KR","Noto Sans CJK JP",
              "Apple SD Gothic Neo",sans-serif;
  color:#31333F;background:#E9EBEF;font-size:16px;line-height:1.6;
  -webkit-font-smoothing:antialiased;
}
/* --- 브라우저 틀 --- */
.browser{width:1280px;margin:0 auto;background:#fff;overflow:hidden;
  box-shadow:0 10px 40px rgba(0,0,0,.12)}
.chrome{background:#E9EBEF;padding:10px 14px;display:flex;align-items:center;gap:12px;
  border-bottom:1px solid #D8DBE0}
.dots{display:flex;gap:6px}
.dots i{width:11px;height:11px;border-radius:50%;display:block}
.bar{flex:1;background:#fff;border-radius:14px;padding:5px 14px;font-size:13px;
  color:#5B5F6B;border:1px solid #D8DBE0}
/* --- 앱 --- */
.app{display:flex;min-height:200px}
.side{width:260px;flex:none;background:#F0F2F6;padding:28px 20px 24px}
.side h3{font-size:1.35rem;font-weight:700;margin-bottom:20px}
.main{flex:1;padding:44px 48px 56px;background:#fff;min-width:0}
h1{font-size:2.3rem;font-weight:700;letter-spacing:-.01em;margin-bottom:6px}
h3.sub{font-size:1.6rem;font-weight:700;margin-bottom:14px}
h4{font-size:1.2rem;font-weight:700;margin:22px 0 10px}
.cap{font-size:.875rem;color:rgba(49,51,63,.6);margin-top:6px}
.lbl{font-size:.875rem;margin-bottom:4px}
/* 입력 */
.inp{border:1px solid rgba(49,51,63,.2);border-radius:.5rem;padding:9px 12px;
  background:#fff;font-size:1rem;color:#31333F}
.inp.ph{color:rgba(49,51,63,.45)}
.sel{position:relative}
.sel:after{content:"▾";position:absolute;right:14px;top:8px;color:rgba(49,51,63,.5)}
/* 버튼 */
.btn{display:inline-block;border:1px solid rgba(49,51,63,.2);border-radius:.5rem;
  padding:8px 18px;background:#fff;font-size:1rem;font-weight:400}
.btn.pri{background:#FF4B4B;border-color:#FF4B4B;color:#fff;font-weight:600}
.btn.w{display:block;text-align:center;width:100%}
/* 라디오 */
.radio{display:flex;gap:22px;align-items:center;flex-wrap:wrap}
.radio span{display:flex;align-items:center;gap:7px;font-size:1rem}
.radio i{width:17px;height:17px;border-radius:50%;border:1px solid rgba(49,51,63,.35);
  background:#fff;display:block;flex:none;position:relative}
.radio i.on{border-color:#FF4B4B;background:#FF4B4B;box-shadow:inset 0 0 0 3.5px #fff}
.vradio span{display:flex;align-items:center;gap:9px;margin-bottom:9px}
/* 탭 */
.tabs{display:flex;gap:26px;border-bottom:1px solid rgba(49,51,63,.15);margin-bottom:20px}
.tabs b{padding-bottom:9px;font-weight:400;color:rgba(49,51,63,.6)}
.tabs b.on{color:#31333F;font-weight:600;box-shadow:inset 0 -2px 0 #FF4B4B}
/* 알림 상자 */
.msg{border-radius:.5rem;padding:13px 16px;font-size:.95rem;margin:12px 0}
.info{background:rgba(28,131,225,.1)}
.ok{background:rgba(33,195,84,.1)}
.warn{background:rgba(255,227,18,.13)}
.err{background:rgba(255,43,43,.09)}
/* 지표 */
.metrics{display:flex;gap:56px;margin:6px 0 4px}
.metric .k{font-size:.875rem;color:rgba(49,51,63,.6)}
.metric .v{font-size:2.2rem;font-weight:600;line-height:1.2}
/* 표 */
table{border-collapse:collapse;width:100%;font-size:.9rem;
  border:1px solid rgba(49,51,63,.12);border-radius:.4rem;overflow:hidden}
th{background:#F0F2F6;text-align:left;padding:8px 12px;font-weight:600;
  color:rgba(49,51,63,.75);border-bottom:1px solid rgba(49,51,63,.12)}
td{padding:8px 12px;border-bottom:1px solid rgba(49,51,63,.08)}
tr:last-child td{border-bottom:none}
/* 진행바 */
.prog{height:7px;background:rgba(49,51,63,.12);border-radius:4px;overflow:hidden;margin:6px 0}
.prog i{display:block;height:100%;background:#FF4B4B}
/* 확장 */
.exp{border:1px solid rgba(49,51,63,.15);border-radius:.5rem;margin-bottom:9px}
.exp .hd{padding:11px 15px;display:flex;justify-content:space-between;font-size:.97rem}
.exp .hd .ch{color:rgba(49,51,63,.5)}
.exp .bd{padding:4px 15px 16px;border-top:1px solid rgba(49,51,63,.1)}
/* 카드(문항) */
.card{border:1px solid rgba(49,51,63,.15);border-radius:.5rem;padding:16px 18px 14px;
  margin-bottom:16px}
.card img{width:100%;display:block;margin-bottom:10px}
/* 타이머 */
.timer{font:700 30px/1.2 -apple-system,system-ui,sans-serif;text-align:center;
  padding:10px;border-radius:10px;background:#f2f4f8;color:#1f2937}
.timer.hot{background:#fee2e2;color:#b91c1c}
/* OMR */
.omr{display:flex;gap:26px}
.omr .paper{flex:1.2;min-width:0;border:1px solid rgba(49,51,63,.12);border-radius:.4rem;
  padding:10px;height:560px;overflow:hidden}
.omr .paper img{width:100%;display:block}
.omr .sheet{flex:1;min-width:0;height:560px;overflow:hidden;padding-right:6px}
.row{display:flex;align-items:center;gap:14px;margin-bottom:11px}
.row .no{width:26px;font-weight:700;text-align:right;flex:none}
/* 문항별 O/X */
.grid{display:flex;flex-wrap:wrap;gap:0}
.grid div{width:9.09%;text-align:center;font-size:.9rem;padding:5px 0}
.grid div b{display:block;font-weight:400;color:rgba(49,51,63,.65);font-size:.8rem}
hr{border:none;border-top:1px solid rgba(49,51,63,.12);margin:26px 0}
.small{font-size:.875rem;color:rgba(49,51,63,.6)}
.chart{width:100%;height:230px;display:block}
"""


def b64(data: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(data).decode()


def radio(options, sel, vertical=False):
    cls = "radio vradio" if vertical else "radio"
    items = "".join(
        f'<span><i class="{"on" if i == sel else ""}"></i>{o}</span>' for i, o in enumerate(options))
    return f'<div class="{cls}">{items}</div>'


def sidebar(name="김민준", active=0):
    menu = ["시험 보기", "결과", "오답노트", "성적 추이"]
    return f"""<div class="side">
      <h3>{name} 학생</h3>
      <div class="lbl">메뉴</div>
      {radio(menu, active, vertical=True)}
      <div style="margin-top:26px"><span class="btn">로그아웃</span></div>
    </div>"""


def page(inner: str, side: str = "") -> str:
    return f"""<html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
    <div class="browser">
      <div class="chrome">
        <div class="dots"><i style="background:#FF5F57"></i><i style="background:#FEBC2E"></i>
        <i style="background:#28C840"></i></div>
        <div class="bar">🔒 {URL}</div>
      </div>
      <div class="app">{side}<div class="main">{inner}</div></div>
    </div></body></html>"""


PHONE_CSS = """
.browser{width:400px}
.main{padding:14px 13px 26px}
h1{font-size:1.75rem}
h3.sub{font-size:1.3rem}
h4{font-size:1.05rem;margin:18px 0 8px}
.metrics{gap:0;justify-content:space-between}
.metric .v{font-size:1.5rem}
.metric .k{font-size:.78rem}
table{font-size:.82rem}
th,td{padding:6px 8px}
.grid div{width:16.6%;font-size:.85rem}
.radio{gap:.45rem .8rem}
.radio span{font-size:1.05rem}
.bar{font-size:12px}
.stickybar{position:sticky;top:0;z-index:9;display:flex;align-items:center;
  justify-content:space-between;gap:10px;padding:9px 12px;border-radius:10px;
  background:#f2f4f8;color:#1f2937;margin-bottom:12px}
.stickybar .t{font-weight:600;font-size:14px;overflow:hidden;white-space:nowrap;
  text-overflow:ellipsis}
.stickybar .c{font-weight:800;font-size:24px;flex:none}
.stickybar.hot{background:#fee2e2;color:#b91c1c}
.hamb{font-size:22px;color:rgba(49,51,63,.7);margin-bottom:10px}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 14px}
.chips span{display:flex;align-items:center;gap:6px;font-size:.95rem}
.chips i{width:15px;height:15px;border-radius:50%;border:1px solid rgba(49,51,63,.35);
  background:#fff;display:block;flex:none}
.chips i.on{border-color:#FF4B4B;background:#FF4B4B;box-shadow:inset 0 0 0 3px #fff}
"""


def phone(inner: str) -> str:
    return f"""<html><head><meta charset="utf-8"><style>{CSS}{PHONE_CSS}</style></head>
    <body><div class="browser">
      <div class="chrome">
        <div class="dots"><i style="background:#FF5F57"></i><i style="background:#FEBC2E"></i>
        <i style="background:#28C840"></i></div>
        <div class="bar">🔒 {URL}</div>
      </div>
      <div class="app"><div class="main">{inner}</div></div>
    </div></body></html>"""


def chips(options, sel):
    items = "".join(f'<span><i class="{"on" if i==sel else ""}"></i>{o}</span>'
                    for i, o in enumerate(options))
    return f'<div class="chips">{items}</div>'


# ------------------------------------------------------------------ 화면들
def s_login():
    inner = f"""
    <h1>📝 시험 · 자동채점</h1>
    <div style="height:18px"></div>
    <div class="tabs"><b class="on">학생</b><b>선생님</b></div>
    <div style="max-width:520px">
      {radio(["기존 학생", "처음 사용"], 0)}
      <div style="height:18px"></div>
      <div class="lbl">이름</div>
      <div class="inp sel">김민준</div>
      <div style="height:14px"></div>
      <div class="lbl">비밀번호 4자리</div>
      <div class="inp">••••</div>
      <div style="height:18px"></div>
      <span class="btn pri w">들어가기</span>
    </div>"""
    return page(inner)


def s_start():
    inner = f"""
    <h3 class="sub">시험 시작</h3>
    <div style="max-width:640px">
      <div class="lbl">시험지</div>
      <div class="inp sel">Q1 · 광성고 대비 1회 (33문항 / 50분)</div>
      <div class="cap">왼쪽에 시험지, 오른쪽에 답안지가 뜹니다. 종이로 출력해 풀어도 되고
        화면의 시험지를 보고 풀어도 됩니다.</div>
      <div class="cap">시작을 누르면 타이머가 돌아가고, 시간이 끝나면 자동으로 제출·채점됩니다.</div>
      <div style="height:18px"></div>
      <span class="btn pri">▶ 시작하기</span>
    </div>"""
    return page(inner, sidebar(active=0))


def s_solve_omr(page_img, qimgs):
    rows = ""
    marks = [2, 0, 4, 1, 2, None, 3, 0, 4, 2]
    for i, m in enumerate(marks, start=1):
        rows += f'<div class="row"><span class="no">{i}</span>' \
                f'{radio(["①", "②", "③", "④", "⑤"], m if m is not None else -1)}</div>'
    rows += ('<div class="row"><span class="no">11</span>'
             '<div class="inp ph" style="flex:1">주관식 — 예) 138, 17/2, 2√7</div></div>'
             '<div class="cap" style="margin:-6px 0 12px 40px">'
             '숫자로 입력 — 예) 138, 17/2, 2√7 (2root7 도 됩니다)</div>')
    inner = f"""
    <div style="display:flex;gap:30px;align-items:flex-start">
      <div style="flex:3"><h3 class="sub">광성고 대비 1회 · 33문항</h3></div>
      <div style="flex:1"><div class="timer hot">04:22</div></div>
    </div>
    <div class="omr" style="margin-top:14px">
      <div style="flex:1.2;min-width:0">
        <div style="font-weight:700;margin-bottom:8px">시험지</div>
        <div class="paper"><img src="{b64(page_img)}"></div>
      </div>
      <div style="flex:1;min-width:0">
        <div style="font-weight:700">답안 표시 (OMR)</div>
        <div class="cap" style="margin:0 0 8px">표시하는 즉시 저장됩니다.</div>
        <div class="sheet">{rows}</div>
      </div>
    </div>
    <div class="prog" style="margin-top:16px"><i style="width:79%"></i></div>
    <div class="small">표시한 문항 26 / 33</div>"""
    return page(inner, sidebar(active=0))


def s_result():
    wrong = {6, 13, 18, 21, 24, 30, 33}
    pend = {17}
    grid = ""
    for n in range(1, 34):
        m = "❌" if n in wrong else ("🟡" if n in pend else "⭕")
        grid += f"<div><b>{n}</b>{m}</div>"
    rows = [("평면좌표", 6, 6), ("직선의 방정식", 10, 12), ("원의 방정식", 5, 10),
            ("도형의 이동", 2, 2), ("미분류", 3, 3)]
    trs = "".join(f"<tr><td>{u}</td><td>{a}</td><td>{b}</td>"
                  f"<td>{round(a/b*100)}</td></tr>" for u, a, b in rows)
    inner = f"""
    <div class="lbl">응시 기록</div>
    <div class="inp sel" style="max-width:520px">Q1 · 2026-09-16 19:41 · 78.8점</div>
    <div style="height:22px"></div>
    <div class="metrics">
      <div class="metric"><div class="k">점수</div><div class="v">78.8점</div></div>
      <div class="metric"><div class="k">맞은 개수</div><div class="v">26 / 33</div></div>
      <div class="metric"><div class="k">선생님 확인 대기</div><div class="v">1문항</div></div>
    </div>
    <h4>단원별 정답률</h4>
    <table><tr><th>단원</th><th>정답</th><th>문항</th><th>정답률(%)</th></tr>{trs}</table>
    <h4>문항별 결과</h4>
    <div class="grid">{grid}</div>
    <div class="cap">⭕ 정답 · ❌ 오답 · 🟡 서술형(선생님 확인)</div>
    <h4>틀린 문항 해설</h4>
    <div class="exp"><div class="hd"><span>6번 · 직선의 방정식 · 내 답 (4,5) / 정답 (4,4)</span>
      <span class="ch">▸</span></div></div>
    <div class="exp"><div class="hd"><span>13번 · 평면좌표 · 내 답 ② / 정답 ①</span>
      <span class="ch">▸</span></div></div>
    <div class="exp"><div class="hd"><span>18번 · 원의 방정식 · 내 답 ⑤ / 정답 ③</span>
      <span class="ch">▸</span></div></div>"""
    return page(inner, sidebar(active=1))


def s_explain(qimg, aimgs):
    body = f'<img src="{b64(qimg)}" style="width:100%;display:block;margin:10px 0 14px">' \
           '<div style="font-weight:700;margin-bottom:8px">해설</div>'
    for a in aimgs:
        body += f'<img src="{b64(a)}" style="width:100%;display:block;margin-bottom:8px">'
    inner = f"""
    <h4 style="margin-top:0">틀린 문항 해설</h4>
    <div class="exp">
      <div class="hd"><span>18번 · 원의 방정식 · 내 답 ⑤ / 정답 ③</span><span class="ch">▾</span></div>
      <div class="bd">{body}</div>
    </div>
    <div class="exp"><div class="hd"><span>21번 · 원의 방정식 · 내 답 ② / 정답 ⑤</span>
      <span class="ch">▸</span></div></div>"""
    return page(inner, sidebar(active=1))


def s_wrongnote(qimg):
    trs = "".join(f"<tr><td>{u}</td><td>{n}</td></tr>" for u, n in
                  [("원의 방정식", 5), ("직선의 방정식", 2), ("평면좌표", 1)])
    inner = f"""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px">
      <span style="width:38px;height:20px;border-radius:11px;background:rgba(49,51,63,.2);
        position:relative;display:inline-block">
        <i style="position:absolute;left:2px;top:2px;width:16px;height:16px;border-radius:50%;
          background:#fff;display:block"></i></span>
      <span>해결한 문항도 보기</span>
    </div>
    <h4 style="margin-top:0">유형별 오답 수</h4>
    <table style="max-width:420px"><tr><th>단원</th><th>오답 수</th></tr>{trs}</table>
    <h4>원의 방정식</h4>
    <div class="exp">
      <div class="hd"><span>Q1 18번  (다시 푼 횟수 1)</span><span class="ch">▾</span></div>
      <div class="bd">
        <img src="{b64(qimg)}" style="width:100%;display:block;margin:10px 0 14px">
        <div class="lbl">다시 풀기</div>
        {radio(["①", "②", "③", "④", "⑤"], 2)}
        <div style="height:14px"></div>
        <span class="btn">채점</span> &nbsp; <span class="btn">해설 보기</span>
        <div class="msg ok" style="max-width:520px">정답입니다. 오답노트에서 해결 처리했습니다.</div>
      </div>
    </div>
    <div class="exp"><div class="hd"><span>Q1 21번  (다시 푼 횟수 0)</span>
      <span class="ch">▸</span></div></div>
    <div class="exp"><div class="hd"><span>Q2 24번  (다시 푼 횟수 0)</span>
      <span class="ch">▸</span></div></div>"""
    return page(inner, sidebar(active=2))


def s_trend():
    pts = [(0, 54.5), (1, 63.6), (2, 72.7), (3, 69.7), (4, 78.8)]
    labels = ["09-02", "09-05", "09-09", "09-12", "09-16"]
    W, H, PAD = 1000, 210, 34
    def x(i): return PAD + i * (W - 2 * PAD) / (len(pts) - 1)
    def y(v): return H - PAD - (v - 40) / 60 * (H - 2 * PAD)
    line = " ".join(f"{x(i):.0f},{y(v):.0f}" for i, v in pts)
    dots = "".join(f'<circle cx="{x(i):.0f}" cy="{y(v):.0f}" r="4" fill="#FF4B4B"/>'
                   for i, v in pts)
    ticks = "".join(
        f'<line x1="{PAD}" y1="{y(g):.0f}" x2="{W-PAD}" y2="{y(g):.0f}" '
        f'stroke="rgba(49,51,63,.12)"/>'
        f'<text x="4" y="{y(g)+4:.0f}" font-size="11" fill="rgba(49,51,63,.55)">{g}</text>'
        for g in (40, 60, 80, 100))
    xl = "".join(f'<text x="{x(i):.0f}" y="{H-10}" font-size="11" text-anchor="middle" '
                 f'fill="rgba(49,51,63,.55)">{labels[i]}</text>' for i, _ in pts)
    trs = "".join(f"<tr><td>2026-{labels[i]} 19:41</td><td>Q{[1,2,11,12,1][i]}</td>"
                  f"<td>{v}</td></tr>" for i, v in pts)
    inner = f"""
    <svg class="chart" viewBox="0 0 {W} {H}" preserveAspectRatio="none">
      {ticks}
      <polyline points="{line}" fill="none" stroke="#FF4B4B" stroke-width="2.5"/>
      {dots}{xl}
    </svg>
    <div style="height:18px"></div>
    <table style="max-width:620px"><tr><th>응시</th><th>시험지</th><th>점수</th></tr>{trs}</table>"""
    return page(inner, sidebar(active=3))


def p_exam(cards):
    body = ""
    for no, data, sel, short in cards:
        ans = ('<div class="inp ph">주관식 — 예) 138, 17/2, 2√7</div>'
               '<div class="cap">숫자로 입력 — 예) 138, 17/2, 2√7 (2root7 도 됩니다)</div>'
               if short else radio(["①", "②", "③", "④", "⑤"], sel))
        body += f"""<div class="card">
          <div style="font-weight:700;margin-bottom:8px">{no}번</div>
          <img src="{b64(data)}">{ans}</div>"""
    inner = f"""
    <div class="hamb">☰</div>
    <div class="stickybar"><span class="t">광성고 대비 1회 · 33문항</span>
      <span class="c">41:07</span></div>
    <div class="exp"><div class="hd"><span>시험지 전체 보기 (인쇄용)</span>
      <span class="ch">▸</span></div></div>
    <div style="height:12px"></div>
    {chips(["1–6 ✓", "7–12 ✓", "13–18 (1)", "19–24", "25–30", "31–33"], 2)}
    <div class="cap" style="margin-bottom:10px">답을 표시하면 바로 저장됩니다.
      창을 닫았다 다시 들어와도 남아 있습니다.</div>
    {body}
    <div class="prog"><i style="width:39%"></i></div>
    <div class="small">표시한 문항 13 / 33</div>
    <div class="msg warn">아직 표시하지 않은 문항 20개가 있습니다. 무응답은 오답으로 처리됩니다.</div>
    <span class="btn pri w">제출하고 채점받기</span>"""
    return phone(inner)


def p_result():
    wrong = {6, 13, 18, 21, 24, 30, 33}
    pend = {17}
    grid = "".join(f'<div><b>{n}</b>{"❌" if n in wrong else ("🟡" if n in pend else "⭕")}</div>'
                   for n in range(1, 34))
    rows = [("평면좌표", 6, 6), ("직선의 방정식", 10, 12), ("원의 방정식", 5, 10),
            ("도형의 이동", 2, 2)]
    trs = "".join(f"<tr><td>{u}</td><td>{a}/{b}</td><td>{round(a/b*100)}%</td></tr>"
                  for u, a, b in rows)
    inner = f"""
    <div class="hamb">☰</div>
    <div class="lbl">응시 기록</div>
    <div class="inp sel">Q1 · 09-16 19:41 · 78.8점</div>
    <div style="height:16px"></div>
    <div class="metrics">
      <div class="metric"><div class="k">점수</div><div class="v">78.8점</div></div>
      <div class="metric"><div class="k">맞은 개수</div><div class="v">26/33</div></div>
      <div class="metric"><div class="k">확인 대기</div><div class="v">1문항</div></div>
    </div>
    <h4>단원별 정답률</h4>
    <table><tr><th>단원</th><th>정답</th><th>비율</th></tr>{trs}</table>
    <h4>문항별 결과</h4>
    <div class="grid">{grid}</div>
    <div class="cap">⭕ 정답 · ❌ 오답 · 🟡 서술형(선생님 확인)</div>
    <h4>틀린 문항 해설</h4>
    <div class="exp"><div class="hd"><span>6번 · 내 답 (4,5) / 정답 (4,4)</span>
      <span class="ch">▸</span></div></div>
    <div class="exp"><div class="hd"><span>13번 · 내 답 ② / 정답 ①</span>
      <span class="ch">▸</span></div></div>
    <div class="exp"><div class="hd"><span>18번 · 내 답 ⑤ / 정답 ③</span>
      <span class="ch">▸</span></div></div>"""
    return phone(inner)


def p_explain(qimg, aimgs):
    body = f'<img src="{b64(qimg)}" style="width:100%;display:block;margin:8px 0 12px">' \
           '<div style="font-weight:700;margin-bottom:6px">해설</div>'
    for a in aimgs:
        body += f'<img src="{b64(a)}" style="width:100%;display:block;margin-bottom:8px">'
    inner = f"""
    <div class="hamb">☰</div>
    <h4 style="margin-top:0">틀린 문항 해설</h4>
    <div class="exp">
      <div class="hd"><span>18번 · 내 답 ⑤ / 정답 ③</span><span class="ch">▾</span></div>
      <div class="bd">{body}</div>
    </div>"""
    return phone(inner)


def p_wrongnote(qimg):
    inner = f"""
    <div class="hamb">☰</div>
    <h4 style="margin-top:0">유형별 오답 수</h4>
    <table><tr><th>단원</th><th>오답 수</th></tr>
      <tr><td>원의 방정식</td><td>5</td></tr>
      <tr><td>직선의 방정식</td><td>2</td></tr>
      <tr><td>평면좌표</td><td>1</td></tr></table>
    <h4>원의 방정식</h4>
    <div class="exp">
      <div class="hd"><span>Q1 18번 (다시 푼 횟수 1)</span><span class="ch">▾</span></div>
      <div class="bd">
        <img src="{b64(qimg)}" style="width:100%;display:block;margin:8px 0 12px">
        <div class="lbl">다시 풀기</div>
        {radio(["①", "②", "③", "④", "⑤"], 2)}
        <div style="height:12px"></div>
        <span class="btn">채점</span> <span class="btn">해설 보기</span>
        <div class="msg ok">정답입니다. 오답노트에서 해결 처리했습니다.</div>
      </div>
    </div>
    <div class="exp"><div class="hd"><span>Q1 21번 (다시 푼 횟수 0)</span>
      <span class="ch">▸</span></div></div>"""
    return phone(inner)


def p_login():
    inner = f"""
    <h1>📝 시험 · 자동채점</h1>
    <div style="height:14px"></div>
    <div class="tabs"><b class="on">학생</b><b>선생님</b></div>
    {radio(["기존 학생", "처음 사용"], 0)}
    <div style="height:14px"></div>
    <div class="lbl">이름</div>
    <div class="inp sel">김민준</div>
    <div style="height:12px"></div>
    <div class="lbl">비밀번호 4자리</div>
    <div class="inp">••••</div>
    <div style="height:16px"></div>
    <span class="btn pri w">들어가기</span>"""
    return phone(inner)


def s_exam_desktop(cards):
    body = ""
    for no, data, sel, short in cards:
        ans = ('<div class="inp ph" style="max-width:420px">주관식 — 예) 138, 17/2, 2√7</div>'
               '<div class="cap">숫자로 입력 — 예) 138, 17/2, 2√7 (2root7 도 됩니다)</div>'
               if short else radio(["①", "②", "③", "④", "⑤"], sel))
        body += f"""<div class="card" style="max-width:820px">
          <div style="font-weight:700;margin-bottom:8px">{no}번</div>
          <img src="{b64(data)}">{ans}</div>"""
    inner = f"""
    <div style="position:sticky;top:0;display:flex;align-items:center;
         justify-content:space-between;gap:12px;padding:9px 14px;border-radius:10px;
         background:#f2f4f8;margin-bottom:14px;max-width:820px">
      <span style="font-weight:600;font-size:15px">광성고 대비 1회 · 33문항</span>
      <span style="font-weight:800;font-size:26px">41:07</span>
    </div>
    <div class="exp" style="max-width:820px"><div class="hd">
      <span>시험지 전체 보기 (인쇄용)</span><span class="ch">▸</span></div></div>
    <div style="height:12px"></div>
    {radio(["1–6 ✓", "7–12 ✓", "13–18 (1)", "19–24", "25–30", "31–33"], 2)}
    <div class="cap" style="margin:10px 0 14px">답을 표시하면 바로 저장됩니다.
      창을 닫았다 다시 들어와도 남아 있습니다.</div>
    {body}
    <div class="prog" style="max-width:820px"><i style="width:39%"></i></div>
    <div class="small">표시한 문항 13 / 33</div>"""
    return page(inner, sidebar(active=0))


# ------------------------------------------------------------------ 실행
def main():
    OUT.mkdir(exist_ok=True)
    core.autoseed()
    q = {n: core.images("Q1", "q", n) for n in (2, 3, 5, 13, 14, 15, 18, 21)}
    pages = core.page_images("Q1")
    a18 = core.images("Q1", "a", 18)

    cards = [(13, q[13][0], 2, False), (14, q[14][0], -1, True),
             (15, q[15][0], -1, False)]
    screens = {
        "폰_1_로그인": p_login(),
        "폰_2_시험화면": p_exam(cards),
        "폰_3_채점결과": p_result(),
        "폰_4_해설": p_explain(q[18][0], a18),
        "폰_5_오답노트": p_wrongnote(q[21][0]),
        "PC_1_시험화면": s_exam_desktop(cards),
        "PC_2_채점결과": s_result(),
    }

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1320, "height": 900}, device_scale_factor=2)
        for name, html in screens.items():
            f = OUT / f"{name}.html"
            f.write_text(html, "utf-8")
            pg.goto(f"file://{f}")
            pg.wait_for_timeout(250)
            el = pg.query_selector(".browser")
            el.screenshot(path=str(OUT / f"{name}.png"))
            print(f"  {name}.png")
            f.unlink()
        b.close()


if __name__ == "__main__":
    main()
