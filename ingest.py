"""시험지 PDF 1개 → DB에 적재.

DB에 들어가는 것
    papers      시험지 정보
    questions   문항별 정답 / 유형 / 단원 (주관식은 needs_check=true)
    paper_files 문항별 문제·해설 이미지, 문제 페이지 전체 이미지

DATABASE_URL 이 설정돼 있으면 그 Postgres로, 없으면 로컬 SQLite로 들어간다.

사용:
    python ingest.py <시험지.pdf> --code Q1 --title "광성고 대비 1회"
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from pdfbackend import Word, get_backend

DATA = Path(__file__).parent / "data"


def trim_bottom(png: bytes, pad: int = 10, min_h: int = 60) -> bytes:
    """문항 이미지 아래쪽 빈 여백을 잘라낸다 (풀이 공간 때문에 크게 남는다)."""
    try:
        import io as _io

        from PIL import Image, ImageChops

        im = Image.open(_io.BytesIO(png))
        gray = im.convert("L")
        bbox = ImageChops.difference(gray, Image.new("L", gray.size, 255)).getbbox()
        if not bbox:
            return png
        bottom = min(im.height, max(min_h, bbox[3] + pad))
        if bottom >= im.height - 2:
            return png
        out = _io.BytesIO()
        im.crop((0, 0, im.width, bottom)).save(out, "PNG")
        return out.getvalue()
    except Exception:
        return png

CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"
ANS_MARK = re.compile(r"^(\d{1,2})\)\s*\[정답\]")
Q_MARK = re.compile(r"^(\d{1,2})\.$")

# 고1 공통수학2 · 도형의 방정식 단원 태깅용 키워드
UNIT_KEYWORDS = {
    "평면좌표": ["무게중심", "내분", "외분", "사이의 거리가", "두 점 사이"],
    "직선의 방정식": ["기울기", "수직이등분선", "직선의 방정식", "y절편", "절편",
                 "평행하", "수직이", "세 직선", "점과 직선"],
    "원의 방정식": ["원의 방정식", "접선", "반지름", "원의 중심", "두 원", "접하"],
    "도형의 이동": ["평행이동", "대칭이동", "대칭인", "대칭하"],
}


@dataclass
class Marker:
    no: int
    page: int
    col: int
    x0: float
    y0: float
    x1: float
    y1: float


def _columns(page_w: float):
    """2단 조판 기준 컬럼 경계 반환."""
    mid = page_w / 2
    return [(0.0, mid), (mid, page_w)]


def _col_of(x0: float, page_w: float) -> int:
    return 0 if x0 < page_w / 2 else 1


def _line_words(words: List[Word], ref: Word, min_x: float) -> List[Word]:
    """ref와 같은 줄, ref 오른쪽에 있는 단어들."""
    out = []
    for w in words:
        if w.x0 < min_x:
            continue
        overlap = min(w.y1, ref.y1) - max(w.y0, ref.y0)
        if overlap > (ref.y1 - ref.y0) * 0.5:
            out.append(w)
    return sorted(out, key=lambda w: w.x0)


def find_markers(be, pdf: Path, pages: range, pattern: re.Pattern) -> List[Marker]:
    found: List[Marker] = []
    for p in pages:
        pw, _ = be.page_size(pdf, p)
        for w in be.words(pdf, p):
            t = unicodedata.normalize("NFKC", w.text).strip()
            m = pattern.match(t)
            if m:
                found.append(
                    Marker(int(m.group(1)), p, _col_of(w.x0, pw), w.x0, w.y0, w.x1, w.y1)
                )
    return found


def detect_explanation_start(be, pdf: Path) -> int:
    n = be.page_count(pdf)
    for p in range(n):
        for w in be.words(pdf, p):
            if ANS_MARK.match(unicodedata.normalize("NFKC", w.text).strip()):
                return p
    return n


def build_segments(be, pdf: Path, markers: List[Marker], pages: range,
                   top_pad=3.0, bottom_margin=74.0, top_margin=64.0):
    """마커별로 (page, rect) 목록 생성. 컬럼/페이지를 넘어가는 항목도 처리."""
    ordered = sorted(markers, key=lambda m: (m.page, m.col, m.y0))
    page_boxes: Dict[int, tuple] = {}
    for p in pages:
        pw, ph = be.page_size(pdf, p)
        page_boxes[p] = (pw, ph)

    segments: Dict[int, List[tuple]] = {}
    for i, m in enumerate(ordered):
        nxt = ordered[i + 1] if i + 1 < len(ordered) else None
        pw, ph = page_boxes[m.page]
        cols = _columns(pw)
        cx0, cx1 = cols[m.col]
        cx0 = max(0.0, cx0 + 4)
        cx1 = min(pw, cx1 - 4)
        segs = []

        if nxt and nxt.page == m.page and nxt.col == m.col:
            segs.append((m.page, (cx0, m.y0 - top_pad, cx1, nxt.y0 - top_pad)))
        else:
            # 이 컬럼 끝까지
            segs.append((m.page, (cx0, m.y0 - top_pad, cx1, ph - bottom_margin)))
            # 이어지는 컬럼/페이지의 위쪽 (다음 마커 직전까지)
            if nxt:
                cur_p, cur_c = m.page, m.col
                while True:
                    if cur_c == 0:
                        cur_c = 1
                    else:
                        cur_p, cur_c = cur_p + 1, 0
                    if cur_p not in page_boxes:
                        break
                    npw, nph = page_boxes[cur_p]
                    ncx0, ncx1 = _columns(npw)[cur_c]
                    ncx0, ncx1 = max(0.0, ncx0 + 4), min(npw, ncx1 - 4)
                    if (cur_p, cur_c) == (nxt.page, nxt.col):
                        if nxt.y0 - top_margin > 8:
                            segs.append((cur_p, (ncx0, top_margin, ncx1, nxt.y0 - top_pad)))
                        break
                    segs.append((cur_p, (ncx0, top_margin, ncx1, nph - bottom_margin)))
                    if cur_p > nxt.page:
                        break
        segments[m.no] = segs
    return segments


def read_answer(be, pdf: Path, m: Marker) -> dict:
    words = be.words(pdf, m.page)
    tail = _line_words(words, Word(m.x0, m.y0, m.x1, m.y1, ""), m.x1 + 0.5)
    raw = " ".join(w.text for w in tail).strip()
    raw = unicodedata.normalize("NFKC", raw) if not any(c in raw for c in CIRCLED) else raw

    for c in CIRCLED:
        if c in raw:
            return {"answer": str(CIRCLED.index(c) + 1), "qtype": "choice",
                    "needs_check": False, "raw": raw}

    cleaned = re.sub(r"\s+", "", raw)
    cleaned = re.sub(r"^\[해설\].*$", "", cleaned)
    ok = bool(cleaned) and bool(re.fullmatch(r"[-+0-9/().,]+", cleaned))
    return {"answer": cleaned if ok else "", "qtype": "short",
            "needs_check": True, "raw": raw}


def guess_unit(text: str) -> str:
    score = {u: 0 for u in UNIT_KEYWORDS}
    for u, kws in UNIT_KEYWORDS.items():
        for k in kws:
            if k in text:
                score[u] += 1
    best = max(score, key=lambda u: score[u])
    return best if score[best] > 0 else "미분류"


def segment_text(be, pdf: Path, segs) -> str:
    out = []
    for p, (x0, y0, x1, y1) in segs:
        for w in be.words(pdf, p):
            if x0 <= w.x0 <= x1 and y0 <= w.y0 <= y1:
                out.append(w.text)
    return " ".join(out)


def ingest(pdf: Path, code: str, title: str, duration: int = 50,
           dpi: int = 150, subject: str = "공통수학", grade: str = "고1",
           quiet: bool = False) -> dict:
    import core

    be = get_backend()
    n_pages = be.page_count(pdf)
    exp_start = detect_explanation_start(be, pdf)
    q_pages = range(0, exp_start)
    a_pages = range(exp_start, n_pages)

    # ---- 해설 ----
    a_markers = find_markers(be, pdf, a_pages, ANS_MARK)
    seen = set()
    a_markers = [m for m in a_markers if not (m.no in seen or seen.add(m.no))]
    a_segs = build_segments(be, pdf, a_markers, a_pages)

    # ---- 문제 ----
    q_markers = find_markers(be, pdf, q_pages, Q_MARK)
    seenq = set()
    q_markers = [m for m in q_markers if not (m.no in seenq or seenq.add(m.no))]
    q_segs = build_segments(be, pdf, q_markers, q_pages, top_margin=68.0)

    questions = []
    files: List[tuple] = []
    for m in sorted(a_markers, key=lambda m: m.no):
        info = read_answer(be, pdf, m)
        segs = a_segs[m.no]
        text = segment_text(be, pdf, segs)
        qtext = segment_text(be, pdf, q_segs[m.no]) if m.no in q_segs else ""

        for i, (p, rect) in enumerate(segs):
            files.append(("a", m.no, i, trim_bottom(be.render_bytes(pdf, p, rect, dpi))))
        if m.no in q_segs:
            for i, (p, rect) in enumerate(q_segs[m.no]):
                files.append(("q", m.no, i,
                              trim_bottom(be.render_bytes(pdf, p, rect, dpi))))

        questions.append({
            "no": m.no,
            "answer": info["answer"],
            "qtype": info["qtype"],
            "needs_check": info["needs_check"],
            "raw": info["raw"][:60],
            "unit": guess_unit(qtext + " " + text),
            "points": 0,  # 0이면 균등 배점
            "n_choices": 5,
        })

    for p in q_pages:
        files.append(("page", p + 1, 0, be.render_bytes(pdf, p, None, 110)))

    meta = {
        "code": code,
        "title": title,
        "subject": subject,
        "grade": grade,
        "duration_min": duration,
        "n_questions": len(questions),
        "n_pages": n_pages,
        "problem_pages": list(range(1, exp_start + 1)),
        "backend": be.name,
        "source_pdf": pdf.name,
    }
    core.put_paper(meta, questions, files)

    need = [q["no"] for q in questions if q["needs_check"]]
    meta["needs_check"] = need
    if not quiet:
        size = sum(len(f[3]) for f in files) / 1e6
        print(f"[{code}] {title}  →  {core.db().kind}")
        print(f"  백엔드      : {be.name}")
        print(f"  문항 수     : {len(questions)}  (문제 {exp_start}p / 해설 {n_pages-exp_start}p)")
        print(f"  이미지      : {len(files)}장 / {size:.1f}MB")
        print(f"  객관식 자동 : {sum(1 for q in questions if q['qtype']=='choice')}개")
        print(f"  손확인 필요 : {need if need else '없음'}  ← 선생님 화면에서 정답 입력")
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--code", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--duration", type=int, default=50)
    ap.add_argument("--dpi", type=int, default=150)
    a = ap.parse_args()
    ingest(Path(a.pdf), a.code, a.title, a.duration, a.dpi)
