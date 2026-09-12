"""data/papers 안의 시험지를 DB로 적재한다.

두 가지 형태를 다 읽는다.
    data/papers/Q1/          폴더 (meta.json, answers.json, q/, a/, page/)
    data/papers/Q1.zip       압축 (앱이 GitHub에 저장할 때 쓰는 형태)

    python seed.py                                   # 로컬 SQLite 로
    DATABASE_URL=postgresql://... python seed.py     # 클라우드 DB 로
"""
from __future__ import annotations

import io
import json
import os
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

import core

SRC = Path(__file__).parent / "data" / "papers"


# ------------------------------------------------------------------ 공통 파서
def _parse(files: Dict[str, bytes]) -> Tuple[dict, List[dict], List[tuple]]:
    """{경로: 바이트} → (meta, questions, files)"""
    meta = json.loads(files["meta.json"].decode("utf-8"))
    qs = json.loads(files["answers.json"].decode("utf-8"))
    out = []
    for name, data in files.items():
        parts = name.replace("\\", "/").split("/")
        if len(parts) != 2 or not parts[1].endswith(".png"):
            continue
        kind, stem = parts[0], parts[1][:-4]
        if kind in ("q", "a"):
            no = int(stem[1:].split("_")[0])
            idx = int(stem.split("_")[1]) if "_" in stem else 0
            out.append((kind, no, idx, data))
        elif kind == "page":
            out.append(("page", int(stem[1:]), 0, data))
    out.sort(key=lambda x: (x[0], x[1], x[2]))
    return meta, qs, out


def load_dir(d: Path):
    files: Dict[str, bytes] = {
        "meta.json": (d / "meta.json").read_bytes(),
        "answers.json": (d / "answers.json").read_bytes(),
    }
    for kind in ("q", "a", "page"):
        sub = d / kind
        if sub.exists():
            for p in sorted(sub.glob("*.png")):
                files[f"{kind}/{p.name}"] = p.read_bytes()
    return _parse(files)


def load_zip(path_or_bytes) -> Tuple[dict, List[dict], List[tuple]]:
    raw = path_or_bytes if isinstance(path_or_bytes, (bytes, bytearray)) \
        else Path(path_or_bytes).read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        return _parse({n: z.read(n) for n in z.namelist() if not n.endswith("/")})


def make_zip(code: str) -> bytes:
    """DB의 시험지 하나를 zip 바이트로. GitHub 저장·백업에 쓴다."""
    meta, qs, files = core.export_paper(code)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr("meta.json", json.dumps(meta, ensure_ascii=False, indent=2))
        z.writestr("answers.json", json.dumps(qs, ensure_ascii=False, indent=2))
        for kind, no, idx, png in files:
            name = f"page/p{no:02d}.png" if kind == "page" \
                else f"{kind}/{kind}{no:02d}_{idx}.png"
            z.writestr(name, png)
    return buf.getvalue()


# ------------------------------------------------------------------ 적재
def sources() -> List[Tuple[str, object]]:
    """(코드, 원본) 목록. 폴더와 zip 을 모두 훑는다."""
    out: List[Tuple[str, object]] = []
    if not SRC.exists():
        return out
    for p in sorted(SRC.iterdir()):
        if p.is_dir() and (p / "meta.json").exists():
            out.append((p.name, p))
        elif p.is_file() and p.suffix.lower() == ".zip":
            out.append((p.stem, p))
    return out


def _load(src) -> Tuple[dict, List[dict], List[tuple]]:
    return load_dir(src) if Path(src).is_dir() else load_zip(src)


def seed_all(quiet: bool = False, only_missing: bool = False) -> int:
    have = set(core.paper_codes()) if only_missing else set()
    total = 0
    for code, src in sources():
        if code in have:
            continue
        try:
            meta, qs, files = _load(src)
        except Exception as e:
            if not quiet:
                print(f"  {code}: 읽기 실패 — {type(e).__name__}: {e}")
            continue
        core.put_paper(meta, qs, files)
        if not quiet:
            mb = sum(len(f[3]) for f in files) / 1e6
            print(f"  {meta['code']:>5}  {meta['title']}  ·  {len(qs)}문항 · "
                  f"이미지 {len(files)}장 ({mb:.1f}MB)")
        total += 1
    return total


def seed_missing(quiet: bool = True) -> int:
    return seed_all(quiet=quiet, only_missing=True)


def main():
    if not sources():
        print("data/papers 에 시험지가 없습니다.")
        sys.exit(1)
    print(f"대상 DB: {core.db().kind}")
    print(f"완료: 시험지 {seed_all()}개")
    if os.environ.get("DATABASE_URL"):
        print("클라우드 DB에 올라갔습니다.")


if __name__ == "__main__":
    main()
