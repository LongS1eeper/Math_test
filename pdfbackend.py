"""PDF 백엔드 추상화.

PyMuPDF(fitz)가 설치돼 있으면 그것을 쓰고, 없으면 poppler-utils
(pdftotext / pdftoppm) 를 사용한다. 둘 다 좌표계가 동일하다.
  - 단위: pt(1/72인치), 원점: 페이지 왼쪽 위, y는 아래로 증가
"""
from __future__ import annotations

import html
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


@dataclass
class Word:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str


class Backend:
    name = "?"

    def page_count(self, pdf: Path) -> int: ...
    def page_size(self, pdf: Path, pno: int) -> Tuple[float, float]: ...
    def words(self, pdf: Path, pno: int) -> List[Word]: ...
    def render(self, pdf: Path, pno: int, rect, out_png: Path, dpi: int = 150) -> Path:
        """rect = (x0, y0, x1, y1) in pt, None이면 페이지 전체."""
        ...

    def render_bytes(self, pdf: Path, pno: int, rect, dpi: int = 150) -> bytes:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            p = self.render(pdf, pno, rect, Path(td) / "x.png", dpi)
            return Path(p).read_bytes()


# --------------------------------------------------------------------------
# PyMuPDF
# --------------------------------------------------------------------------
class FitzBackend(Backend):
    name = "pymupdf"

    def __init__(self):
        import fitz  # noqa

        self.fitz = fitz
        self._cache = {}

    def _doc(self, pdf: Path):
        key = str(pdf)
        if key not in self._cache:
            self._cache[key] = self.fitz.open(str(pdf))
        return self._cache[key]

    def page_count(self, pdf: Path) -> int:
        return self._doc(pdf).page_count

    def page_size(self, pdf: Path, pno: int):
        r = self._doc(pdf)[pno].rect
        return (r.width, r.height)

    def words(self, pdf: Path, pno: int) -> List[Word]:
        out = []
        for w in self._doc(pdf)[pno].get_text("words"):
            x0, y0, x1, y1, txt = w[0], w[1], w[2], w[3], w[4]
            out.append(Word(x0, y0, x1, y1, txt))
        return out

    def render(self, pdf: Path, pno: int, rect, out_png: Path, dpi: int = 150) -> Path:
        page = self._doc(pdf)[pno]
        clip = self.fitz.Rect(*rect) if rect else None
        pix = page.get_pixmap(dpi=dpi, clip=clip)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(out_png))
        return out_png

    def render_bytes(self, pdf: Path, pno: int, rect, dpi: int = 150) -> bytes:
        page = self._doc(pdf)[pno]
        clip = self.fitz.Rect(*rect) if rect else None
        return page.get_pixmap(dpi=dpi, clip=clip).tobytes("png")


# --------------------------------------------------------------------------
# poppler-utils
# --------------------------------------------------------------------------
_WORD_RE = re.compile(
    r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>'
)
_PAGE_RE = re.compile(r'<page width="([\d.]+)" height="([\d.]+)"')


class PopplerBackend(Backend):
    name = "poppler"

    def __init__(self):
        for exe in ("pdftotext", "pdftoppm", "pdfinfo"):
            if not shutil.which(exe):
                raise RuntimeError(f"{exe} 를 찾을 수 없습니다 (poppler-utils 설치 필요)")

    def page_count(self, pdf: Path) -> int:
        out = subprocess.run(
            ["pdfinfo", str(pdf)], capture_output=True, text=True
        ).stdout
        m = re.search(r"Pages:\s+(\d+)", out)
        return int(m.group(1)) if m else 0

    def _bbox_xml(self, pdf: Path, pno: int) -> str:
        return subprocess.run(
            ["pdftotext", "-bbox", "-f", str(pno + 1), "-l", str(pno + 1), str(pdf), "-"],
            capture_output=True,
            text=True,
        ).stdout

    def page_size(self, pdf: Path, pno: int):
        m = _PAGE_RE.search(self._bbox_xml(pdf, pno))
        return (float(m.group(1)), float(m.group(2))) if m else (595.0, 841.0)

    def words(self, pdf: Path, pno: int) -> List[Word]:
        xml = self._bbox_xml(pdf, pno)
        out = []
        for m in _WORD_RE.finditer(xml):
            out.append(
                Word(
                    float(m.group(1)),
                    float(m.group(2)),
                    float(m.group(3)),
                    float(m.group(4)),
                    html.unescape(m.group(5)),
                )
            )
        return out

    def render(self, pdf: Path, pno: int, rect, out_png: Path, dpi: int = 150) -> Path:
        out_png.parent.mkdir(parents=True, exist_ok=True)
        stem = out_png.with_suffix("")
        cmd = [
            "pdftoppm", "-png", "-r", str(dpi),
            "-f", str(pno + 1), "-l", str(pno + 1),
            "-singlefile",
        ]
        if rect:
            s = dpi / 72.0
            x0, y0, x1, y1 = rect
            cmd += [
                "-x", str(int(x0 * s)),
                "-y", str(int(y0 * s)),
                "-W", str(max(1, int((x1 - x0) * s))),
                "-H", str(max(1, int((y1 - y0) * s))),
            ]
        cmd += [str(pdf), str(stem)]
        subprocess.run(cmd, check=True, capture_output=True)
        return out_png


def get_backend() -> Backend:
    try:
        return FitzBackend()
    except Exception:
        return PopplerBackend()
