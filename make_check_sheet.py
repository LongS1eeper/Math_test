"""needs_check 문항의 [정답] 줄만 잘라 한 장으로 모아 준다 (선생님 확인용)."""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from ingest import ANS_MARK, detect_explanation_start, find_markers
from pdfbackend import get_backend

DATA = Path(__file__).parent / "data"


def build(code: str, pdf: Path, height_pt: float = 46.0, dpi: int = 170):
    be = get_backend()
    qs = json.load(open(DATA / "papers" / code / "answers.json", encoding="utf-8"))
    need = {q["no"] for q in qs if q["needs_check"]}
    start = detect_explanation_start(be, pdf)
    markers = find_markers(be, pdf, range(start, be.page_count(pdf)), ANS_MARK)
    seen, ms = set(), []
    for m in markers:
        if m.no in need and m.no not in seen:
            seen.add(m.no)
            ms.append(m)
    ms.sort(key=lambda m: m.no)

    out = DATA / "papers" / code / "_check"
    out.mkdir(parents=True, exist_ok=True)
    tiles = []
    for m in ms:
        pw, ph = be.page_size(pdf, m.page)
        x0 = 4 if m.col == 0 else pw / 2 + 4
        x1 = pw / 2 - 4 if m.col == 0 else pw - 4
        rect = (x0, m.y0 - 3, x1, min(ph - 74, m.y0 + height_pt))
        p = be.render(pdf, m.page, rect, out / f"{m.no:02d}.png", dpi)
        tiles.append((m.no, Image.open(p).convert("RGB")))

    if not tiles:
        return None
    w = max(t.width for _, t in tiles)
    h = sum(t.height + 6 for _, t in tiles)
    sheet = Image.new("RGB", (w, h), "white")
    y = 0
    d = ImageDraw.Draw(sheet)
    for no, t in tiles:
        sheet.paste(t, (0, y))
        d.line([(0, y + t.height + 3), (w, y + t.height + 3)], fill=(200, 200, 200))
        y += t.height + 6
    path = DATA / "papers" / code / "_check" / "sheet.png"
    sheet.save(path)
    print(path, [no for no, _ in tiles])
    return path


if __name__ == "__main__":
    build(sys.argv[1], Path(sys.argv[2]))
