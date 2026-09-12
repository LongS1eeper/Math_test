"""제출·채점 알림.

보내는 곳은 두 가지. 설정된 것만 보내고, 아무것도 설정 안 하면 조용히 넘어간다.
채점은 알림 실패와 무관하게 항상 정상 동작한다.

  메일    MAIL_TO · MAIL_USER · MAIL_PASS · MAIL_HOST · MAIL_PORT
  텔레그램 TELEGRAM_BOT_TOKEN · TELEGRAM_CHAT_ID

값은 환경변수 → Streamlit secrets → DB settings 순으로 찾는다.
"""
from __future__ import annotations

import os
import smtplib
import socket
from email.message import EmailMessage
from email.utils import formataddr
from typing import Dict, List, Optional, Tuple

import core

TIMEOUT = 15

# 메일 제공자별 기본값 (계정만 넣으면 되게)
PRESETS: Dict[str, Dict[str, str]] = {
    "네이버": {"host": "smtp.naver.com", "port": "465"},
    "지메일": {"host": "smtp.gmail.com", "port": "465"},
    "다음/카카오": {"host": "smtp.daum.net", "port": "465"},
    "직접 입력": {"host": "", "port": "465"},
}

SETUP_HELP = {
    "네이버": "네이버 메일 → 환경설정 → POP3/IMAP 설정에서 **IMAP/SMTP 사용함**으로 켜세요. "
            "2단계 인증을 쓰신다면 로그인 비밀번호 대신 **애플리케이션 비밀번호**를 넣어야 합니다.",
    "지메일": "구글 계정 보안에서 2단계 인증을 켠 뒤 **앱 비밀번호** 16자리를 발급받아 넣으세요. "
            "일반 로그인 비밀번호로는 더 이상 안 됩니다.",
    "다음/카카오": "다음 메일 → 환경설정 → IMAP/SMTP 설정을 켜고, 2단계 인증 시 앱 비밀번호를 쓰세요.",
    "직접 입력": "메일 제공자가 안내하는 SMTP 주소와 포트(SSL 465 또는 TLS 587)를 넣으세요.",
}


# ------------------------------------------------------------------ 설정 읽기
def cfg(key: str) -> str:
    v = os.environ.get(key, "")
    if not v:
        try:
            import streamlit as st
            v = str(st.secrets.get(key, ""))
        except Exception:
            v = ""
    if not v:
        v = core.setting(key.lower(), "")
    return str(v).strip()


def email_ready() -> bool:
    return all(cfg(k) for k in ("MAIL_TO", "MAIL_USER", "MAIL_PASS", "MAIL_HOST"))


def telegram_ready() -> bool:
    return bool(cfg("TELEGRAM_BOT_TOKEN") and cfg("TELEGRAM_CHAT_ID"))


def channels() -> List[str]:
    out = []
    if email_ready():
        out.append("메일")
    if telegram_ready():
        out.append("텔레그램")
    return out


def configured() -> bool:
    return bool(channels())


# ------------------------------------------------------------------ 메일
def send_email(subject: str, body: str) -> Tuple[bool, str]:
    to = cfg("MAIL_TO")
    user = cfg("MAIL_USER")
    pw = cfg("MAIL_PASS")
    host = cfg("MAIL_HOST")
    port = int(cfg("MAIL_PORT") or 465)
    if not (to and user and pw and host):
        return False, "메일 설정이 비어 있습니다."

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr(("시험 자동채점", cfg("MAIL_FROM") or user))
    msg["To"] = to
    msg.set_content(body)

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=TIMEOUT) as s:
                s.login(user, pw)
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=TIMEOUT) as s:
                s.starttls()
                s.login(user, pw)
                s.send_message(msg)
        return True, f"{to} 로 보냈습니다."
    except smtplib.SMTPAuthenticationError:
        return False, ("로그인이 거절됐습니다. 메일 설정에서 IMAP/SMTP 사용을 켰는지, "
                       "2단계 인증을 쓴다면 로그인 비밀번호가 아니라 "
                       "애플리케이션(앱) 비밀번호를 넣었는지 확인하세요.")
    except (socket.timeout, TimeoutError):
        return False, f"{host}:{port} 에 연결하지 못했습니다. 주소·포트를 확인하세요."
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"[:300]


# ------------------------------------------------------------------ 텔레그램
TG = "https://api.telegram.org/bot{token}/{method}"


def send_telegram(text: str) -> Tuple[bool, str]:
    import requests

    token, chat = cfg("TELEGRAM_BOT_TOKEN"), cfg("TELEGRAM_CHAT_ID")
    if not token:
        return False, "봇 토큰이 없습니다."
    if not chat:
        return False, "chat id 가 없습니다."
    try:
        r = requests.post(TG.format(token=token, method="sendMessage"),
                          json={"chat_id": chat, "text": text,
                                "disable_web_page_preview": True},
                          timeout=TIMEOUT)
        j = r.json()
        return (True, "보냈습니다.") if j.get("ok") \
            else (False, str(j.get("description", j))[:200])
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"[:200]


def find_chat_ids() -> Tuple[List[dict], str]:
    """봇에게 아무 메시지나 보낸 뒤 호출하면 chat id 목록이 나온다."""
    import requests

    token = cfg("TELEGRAM_BOT_TOKEN")
    if not token:
        return [], "봇 토큰을 먼저 넣어 주세요."
    try:
        j = requests.get(TG.format(token=token, method="getUpdates"),
                         timeout=TIMEOUT).json()
        if not j.get("ok"):
            return [], str(j.get("description", j))[:200]
        seen, out = set(), []
        for u in j.get("result", []):
            ch = (u.get("message") or u.get("edited_message") or {}).get("chat")
            if ch and ch["id"] not in seen:
                seen.add(ch["id"])
                out.append({"chat_id": str(ch["id"]),
                            "이름": ch.get("first_name") or ch.get("title") or "",
                            "종류": ch.get("type", "")})
        if not out:
            return [], "봇에게 아무 메시지나 한 번 보낸 뒤 다시 눌러 주세요."
        return out, f"{len(out)}개를 찾았습니다."
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"[:200]


# ------------------------------------------------------------------ 발송
def send(subject: str, body: str) -> Tuple[bool, str]:
    """설정된 곳 모두로 보낸다. 하나라도 성공하면 True."""
    results = []
    if email_ready():
        ok, m = send_email(subject, body)
        results.append((ok, f"메일: {m}"))
    if telegram_ready():
        ok, m = send_telegram(f"{subject}\n\n{body}")
        results.append((ok, f"텔레그램: {m}"))
    if not results:
        return False, "알림 받을 곳이 설정돼 있지 않습니다. 선생님 → 설정에서 지정하세요."
    return any(ok for ok, _ in results), " / ".join(m for _, m in results)


# ------------------------------------------------------------------ 메시지
def submission_subject(student: str, paper_title: str, score: float) -> str:
    return f"[채점] {student} · {paper_title} · {score}점"


def submission_body(student: str, paper_title: str, result: dict,
                    units: dict, app_url: str = "") -> str:
    score = result["score"]
    icon = "🟢" if score >= 80 else ("🟡" if score >= 60 else "🔴")
    lines = [
        f"{icon} {student} · {paper_title}",
        f"{score}점  ({result['correct']}/{result['gradable']})",
    ]
    if result.get("auto"):
        lines.append("⏱ 시간 종료로 자동 제출")
    if result["wrong"]:
        nums = ", ".join(str(n) for n in result["wrong"])
        lines.append(f"틀린 문항 {len(result['wrong'])}개 — {nums}")
    else:
        lines.append("틀린 문항 없음")
    weak = [f"{u} {a}/{b}" for u, (a, b) in units.items() if b and a / b < 0.7]
    if weak:
        lines.append("약한 단원 — " + " · ".join(weak))
    if result["pending"]:
        lines.append(f"✍️ 선생님 확인 대기 {len(result['pending'])}문항")
    if app_url:
        lines += ["", app_url]
    return "\n".join(lines)


def notify_submission(attempt_id: int) -> Tuple[bool, str]:
    """채점 직후 호출. 이미 보낸 응시는 다시 보내지 않는다."""
    if not configured():
        return False, "알림 설정 없음"
    d = core.db()
    a = d.one("SELECT a.*, s.name FROM attempts a JOIN students s ON s.id=a.student_id "
              "WHERE a.id=?", (attempt_id,))
    if a is None:
        return False, "응시 기록이 없습니다."
    if a.get("notified"):
        return False, "이미 발송한 응시입니다."

    meta, _ = core.load_paper(a["paper_code"])
    resp = core.get_responses(attempt_id)
    result = {
        "score": a["score"],
        "correct": sum(1 for r in resp.values() if r["is_correct"] == 1),
        "gradable": sum(1 for r in resp.values() if r["is_correct"] is not None),
        "wrong": sorted(n for n, r in resp.items() if r["is_correct"] == 0),
        "pending": [n for n, r in resp.items() if r["is_correct"] is None],
        "auto": bool(a["auto_submitted"]),
    }
    ok, msg = send(
        submission_subject(a["name"], meta["title"], a["score"]),
        submission_body(a["name"], meta["title"], result,
                        core.unit_stats(attempt_id), cfg("APP_URL")))
    if ok:
        d.exec("UPDATE attempts SET notified=1 WHERE id=?", (attempt_id,))
    return ok, msg
