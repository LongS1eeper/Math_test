"""GitHub 저장소를 시험지 보관소로 쓴다.

앱에서 시험지를 등록하면 `data/papers/<코드>.zip` 으로 저장소에 커밋한다.
서버가 재시작해도 저장소에서 다시 읽히므로 시험지가 계속 쌓인다.

설정 (환경변수 · Streamlit secrets · 앱 설정 화면)
    GITHUB_TOKEN   개인 액세스 토큰 — Contents 권한 읽기/쓰기
    GITHUB_REPO    소유자/저장소     예) LongS1eeper/exam-app
    GITHUB_BRANCH  기본값 main
"""
from __future__ import annotations

import base64
from typing import Dict, List, Optional, Tuple

import requests

import core

API = "https://api.github.com"
DIR = "data/papers"
TIMEOUT = 60


def cfg(key: str, default: str = "") -> str:
    import notify
    return notify.cfg(key) or default


def repo() -> str:
    return cfg("GITHUB_REPO")


def branch() -> str:
    return cfg("GITHUB_BRANCH", "main")


def configured() -> bool:
    return bool(cfg("GITHUB_TOKEN") and "/" in repo())


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {cfg('GITHUB_TOKEN')}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _err(r) -> str:
    try:
        j = r.json()
        msg = j.get("message", "")
        if r.status_code == 401:
            return "토큰이 거절됐습니다 (401). 토큰을 다시 발급해 넣어 주세요."
        if r.status_code == 403:
            return f"권한이 없습니다 (403). 토큰에 Contents 쓰기 권한이 있는지 확인하세요. {msg}"
        if r.status_code == 404:
            return ("저장소를 찾을 수 없습니다 (404). 소유자/저장소 이름과, "
                    "비공개 저장소라면 토큰이 그 저장소에 접근 가능한지 확인하세요.")
        if r.status_code == 409:
            return "저장소가 비어 있습니다. 먼저 코드를 한 번 push 해 주세요."
        return f"{r.status_code} {msg}"[:300]
    except Exception:
        return f"{r.status_code}"[:300]


# ------------------------------------------------------------------ 조회
def check() -> Tuple[bool, str]:
    """연결·권한 확인."""
    if not cfg("GITHUB_TOKEN"):
        return False, "토큰이 비어 있습니다."
    if "/" not in repo():
        return False, "저장소를 '소유자/저장소' 형태로 넣어 주세요. 예) LongS1eeper/exam-app"
    try:
        r = requests.get(f"{API}/repos/{repo()}", headers=_headers(), timeout=TIMEOUT)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"[:200]
    if r.status_code != 200:
        return False, _err(r)
    j = r.json()
    perms = j.get("permissions", {})
    if not perms.get("push", False):
        return False, "이 저장소에 쓰기 권한이 없는 토큰입니다."
    kind = "비공개" if j.get("private") else "공개"
    return True, f"{j['full_name']} ({kind}) · 브랜치 {branch()} · 쓰기 권한 OK"


def remote_files() -> Tuple[Dict[str, dict], str]:
    """저장소의 data/papers 목록 → {파일명: {sha, size}}"""
    try:
        r = requests.get(f"{API}/repos/{repo()}/contents/{DIR}",
                         headers=_headers(), params={"ref": branch()}, timeout=TIMEOUT)
    except Exception as e:
        return {}, f"{type(e).__name__}: {e}"[:200]
    if r.status_code == 404:
        return {}, ""                      # 아직 폴더가 없음 — 정상
    if r.status_code != 200:
        return {}, _err(r)
    out = {}
    for it in r.json():
        if it.get("type") == "file":
            out[it["name"]] = {"sha": it["sha"], "size": it.get("size", 0)}
    return out, ""


# ------------------------------------------------------------------ 저장
def push_paper(code: str, message: Optional[str] = None) -> Tuple[bool, str]:
    """DB의 시험지 하나를 zip 으로 만들어 저장소에 커밋."""
    if not configured():
        return False, "GitHub 설정이 없습니다."
    import seed

    try:
        blob = seed.make_zip(code)
    except Exception as e:
        return False, f"zip 생성 실패 — {type(e).__name__}: {e}"[:200]
    if len(blob) > 45 * 1024 * 1024:
        return False, f"{len(blob)/1e6:.0f}MB 라 너무 큽니다. ingest 의 dpi 를 낮춰 주세요."

    name = f"{code}.zip"
    existing, err = remote_files()
    if err:
        return False, err

    body = {
        "message": message or f"시험지 {code} 저장",
        "content": base64.b64encode(blob).decode("ascii"),
        "branch": branch(),
    }
    if name in existing:
        body["sha"] = existing[name]["sha"]

    try:
        r = requests.put(f"{API}/repos/{repo()}/contents/{DIR}/{name}",
                         headers=_headers(), json=body, timeout=TIMEOUT)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"[:200]
    if r.status_code not in (200, 201):
        return False, _err(r)
    what = "수정" if name in existing else "추가"
    return True, f"{name} {what} 완료 ({len(blob)/1e6:.1f}MB)"


def push_all() -> Tuple[int, List[str]]:
    ok, msgs = 0, []
    for code in core.paper_codes():
        good, m = push_paper(code)
        msgs.append(f"{code}: {m}")
        ok += 1 if good else 0
    return ok, msgs


def delete_paper(code: str) -> Tuple[bool, str]:
    if not configured():
        return False, "GitHub 설정이 없습니다."
    name = f"{code}.zip"
    existing, err = remote_files()
    if err:
        return False, err
    if name not in existing:
        return True, "저장소에는 없습니다."
    try:
        r = requests.delete(
            f"{API}/repos/{repo()}/contents/{DIR}/{name}",
            headers=_headers(),
            json={"message": f"시험지 {code} 삭제", "sha": existing[name]["sha"],
                  "branch": branch()},
            timeout=TIMEOUT)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"[:200]
    return (True, f"{name} 삭제 완료") if r.status_code == 200 else (False, _err(r))


def status() -> Tuple[List[dict], str]:
    """DB와 저장소를 나란히 비교한 표."""
    remote, err = remote_files()
    if err:
        return [], err
    codes = sorted(set(core.paper_codes()) | {n[:-4] for n in remote if n.endswith(".zip")})
    rows = []
    for c in codes:
        in_db = c in core.paper_codes()
        r = remote.get(f"{c}.zip")
        rows.append({
            "시험지": c,
            "앱": "○" if in_db else "",
            "저장소": f"{r['size']/1e6:.1f}MB" if r else "",
            "상태": "저장됨" if (in_db and r) else ("저장 안 됨" if in_db else "앱에 없음"),
        })
    return rows, ""
