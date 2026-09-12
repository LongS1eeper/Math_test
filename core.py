"""DB 계층 + 채점 로직 (Streamlit 비의존 — 단독 테스트 가능).

DB 선택
    DATABASE_URL 환경변수(또는 Streamlit secrets)에 postgres:// 주소가 있으면 → Postgres
    없으면 → 로컬 SQLite (data/exam.db)

시험지(문제·해설 이미지 포함)도 DB에 들어간다. 그래서
  · Streamlit Cloud가 재시작해도 사라지지 않고
  · 저작권 있는 자료가 GitHub 저장소에 올라가지 않는다.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE = Path(__file__).parent
DATA = BASE / "data"

# ---------------------------------------------------------------- 스키마
SCHEMA = """
CREATE TABLE IF NOT EXISTS papers(
  code TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  subject TEXT, grade TEXT,
  duration_min INTEGER NOT NULL DEFAULT 50,
  n_questions INTEGER NOT NULL DEFAULT 0,
  meta TEXT,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS questions(
  code TEXT NOT NULL, no INTEGER NOT NULL,
  qtype TEXT NOT NULL, answer TEXT, unit TEXT,
  needs_check INTEGER DEFAULT 0, n_choices INTEGER DEFAULT 5,
  PRIMARY KEY(code, no)
);
CREATE TABLE IF NOT EXISTS paper_files(
  code TEXT NOT NULL, kind TEXT NOT NULL,
  no INTEGER NOT NULL, idx INTEGER NOT NULL,
  png {BLOB} NOT NULL,
  PRIMARY KEY(code, kind, no, idx)
);
CREATE TABLE IF NOT EXISTS students(
  id {ID}, name TEXT UNIQUE NOT NULL, pin TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS attempts(
  id {ID},
  student_id INTEGER NOT NULL, paper_code TEXT NOT NULL,
  started_at TEXT NOT NULL, deadline TEXT NOT NULL,
  submitted_at TEXT, auto_submitted INTEGER DEFAULT 0,
  score REAL, total REAL,
  status TEXT NOT NULL DEFAULT 'ongoing',
  teacher_seen INTEGER DEFAULT 0,
  notified INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS responses(
  attempt_id INTEGER NOT NULL, no INTEGER NOT NULL,
  answer TEXT, is_correct INTEGER,
  PRIMARY KEY(attempt_id, no)
);
CREATE TABLE IF NOT EXISTS wrongnotes(
  id {ID},
  student_id INTEGER NOT NULL, paper_code TEXT NOT NULL, no INTEGER NOT NULL,
  unit TEXT, created_at TEXT NOT NULL, resolved_at TEXT,
  retry_count INTEGER DEFAULT 0, memo TEXT,
  UNIQUE(student_id, paper_code, no)
);
CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
"""


def _split(sql: str) -> List[str]:
    return [s.strip() for s in sql.split(";") if s.strip()]


def to_pg(sql: str) -> str:
    """`?` 자리표시자를 `%s` 로. 문자열 리터럴 안의 ? 는 건드리지 않는다."""
    out, in_str, quote = [], False, ""
    for ch in sql:
        if in_str:
            out.append(ch)
            if ch == quote:
                in_str = False
        elif ch in ("'", '"'):
            in_str, quote = True, ch
            out.append(ch)
        elif ch == "?":
            out.append("%s")
        else:
            out.append(ch)
    return "".join(out)


# ---------------------------------------------------------------- DB
class DB:
    def __init__(self, url: Optional[str] = None):
        self.url = url or os.environ.get("DATABASE_URL", "")
        self.pg = self.url.startswith(("postgres://", "postgresql://"))
        if self.pg:
            import psycopg2
            import psycopg2.extras
            self._psycopg2 = psycopg2
            self.conn = psycopg2.connect(self.url, sslmode="require")
            self.conn.autocommit = True
            self._factory = psycopg2.extras.RealDictCursor
            schema = SCHEMA.replace("{ID}", "SERIAL PRIMARY KEY").replace("{BLOB}", "BYTEA")
        else:
            DATA.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(DATA / "exam.db", check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            schema = SCHEMA.replace("{ID}", "INTEGER PRIMARY KEY AUTOINCREMENT") \
                           .replace("{BLOB}", "BLOB")
        for stmt in _split(schema):
            self.exec(stmt)
        # 예전 버전 DB에서 넘어온 경우를 위한 보강
        self.ensure_column("attempts", "notified", "INTEGER DEFAULT 0")

    def ensure_column(self, table: str, col: str, decl: str):
        if self.pg:
            hit = self.one("SELECT 1 AS x FROM information_schema.columns "
                           "WHERE table_name=? AND column_name=?", (table, col))
        else:
            cols = [c["name"] for c in self.query(f"PRAGMA table_info({table})")]
            hit = {"x": 1} if col in cols else None
        if not hit:
            self.exec(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")

    # -- 내부
    def _cur(self):
        return self.conn.cursor(cursor_factory=self._factory) if self.pg \
            else self.conn.cursor()

    def _prep(self, sql: str) -> str:
        return to_pg(sql) if self.pg else sql

    @staticmethod
    def _row(r) -> Dict[str, Any]:
        d = dict(r)
        for k, v in d.items():
            if isinstance(v, memoryview):
                d[k] = bytes(v)
        return d

    # -- 공개
    def exec(self, sql: str, params=()) -> None:
        cur = self._cur()
        cur.execute(self._prep(sql), tuple(params))
        if not self.pg:
            self.conn.commit()
        cur.close()

    def query(self, sql: str, params=()) -> List[Dict[str, Any]]:
        cur = self._cur()
        cur.execute(self._prep(sql), tuple(params))
        rows = [self._row(r) for r in cur.fetchall()]
        cur.close()
        return rows

    def one(self, sql: str, params=()) -> Optional[Dict[str, Any]]:
        r = self.query(sql, params)
        return r[0] if r else None

    def insert_id(self, sql: str, params=()) -> int:
        """INSERT 후 새 id 반환. sql 끝에 RETURNING 을 붙이지 말 것."""
        cur = self._cur()
        if self.pg:
            cur.execute(self._prep(sql) + " RETURNING id", tuple(params))
            new = cur.fetchone()["id"]
        else:
            cur.execute(sql, tuple(params))
            self.conn.commit()
            new = cur.lastrowid
        cur.close()
        return int(new)

    @property
    def kind(self) -> str:
        return "PostgreSQL" if self.pg else "SQLite"


_db: Optional[DB] = None


def db(url: Optional[str] = None) -> DB:
    global _db
    if _db is None or (url and url != _db.url):
        _db = DB(url)
    return _db


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def setting(key: str, default: str = "") -> str:
    r = db().one("SELECT v FROM settings WHERE k=?", (key,))
    return r["v"] if r else default


def set_setting(key: str, val: str):
    d = db()
    d.exec("INSERT INTO settings(k,v) VALUES(?,?) "
           "ON CONFLICT(k) DO UPDATE SET v=excluded.v", (key, val))


# ---------------------------------------------------------------- 시험지
def list_papers() -> List[dict]:
    return db().query("SELECT code,title,subject,grade,duration_min,n_questions,updated_at "
                      "FROM papers ORDER BY code")


def load_paper(code: str) -> tuple[dict, List[dict]]:
    meta = db().one("SELECT * FROM papers WHERE code=?", (code,))
    if meta is None:
        raise KeyError(code)
    if meta.get("meta"):
        meta.update(json.loads(meta["meta"]))
    qs = db().query("SELECT no,qtype,answer,unit,needs_check,n_choices "
                    "FROM questions WHERE code=? ORDER BY no", (code,))
    for q in qs:
        q["needs_check"] = bool(q["needs_check"])
        q["answer"] = q["answer"] or ""
    return meta, qs


def save_answers(code: str, qs: List[dict]):
    d = db()
    for q in qs:
        d.exec("INSERT INTO questions(code,no,qtype,answer,unit,needs_check,n_choices) "
               "VALUES(?,?,?,?,?,?,?) ON CONFLICT(code,no) DO UPDATE SET "
               "qtype=excluded.qtype, answer=excluded.answer, unit=excluded.unit, "
               "needs_check=excluded.needs_check",
               (code, q["no"], q["qtype"], q["answer"], q.get("unit", ""),
                1 if q.get("needs_check") else 0, q.get("n_choices", 5)))


def put_paper(meta: dict, questions: List[dict], files: List[tuple]):
    """files: [(kind, no, idx, png_bytes), ...]  — 시험지 전체를 통째로 갈아끼운다."""
    d = db()
    code = meta["code"]
    d.exec("DELETE FROM paper_files WHERE code=?", (code,))
    d.exec("DELETE FROM questions WHERE code=?", (code,))
    d.exec("INSERT INTO papers(code,title,subject,grade,duration_min,n_questions,meta,updated_at) "
           "VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(code) DO UPDATE SET "
           "title=excluded.title, subject=excluded.subject, grade=excluded.grade, "
           "duration_min=excluded.duration_min, n_questions=excluded.n_questions, "
           "meta=excluded.meta, updated_at=excluded.updated_at",
           (code, meta["title"], meta.get("subject", ""), meta.get("grade", ""),
            int(meta.get("duration_min", 50)), len(questions),
            json.dumps(meta, ensure_ascii=False), now()))
    save_answers(code, questions)
    for kind, no, idx, png in files:
        d.exec("INSERT INTO paper_files(code,kind,no,idx,png) VALUES(?,?,?,?,?)",
               (code, kind, no, idx, _blob(png)))


def _blob(b: bytes):
    return b if not db().pg else db()._psycopg2.Binary(b)


def delete_paper(code: str):
    d = db()
    for t in ("paper_files", "questions"):
        d.exec(f"DELETE FROM {t} WHERE code=?", (code,))
    d.exec("DELETE FROM papers WHERE code=?", (code,))


def export_paper(code: str) -> tuple[dict, List[dict], List[tuple]]:
    """시험지 하나를 (meta, questions, files) 로 꺼낸다. 백업·GitHub 저장용."""
    meta, qs = load_paper(code)
    meta.pop("meta", None)
    rows = db().query("SELECT kind,no,idx,png FROM paper_files WHERE code=? "
                      "ORDER BY kind,no,idx", (code,))
    files = [(r["kind"], r["no"], r["idx"], r["png"]) for r in rows]
    return meta, qs, files


def paper_codes() -> List[str]:
    return [p["code"] for p in list_papers()]


def autoseed() -> int:
    """DB가 비어 있고 저장소에 data/papers 가 있으면 자동으로 채운다.

    Streamlit Cloud처럼 서버가 재시작되며 파일이 초기화되는 곳에서,
    별도 DB 없이도 시험지가 항상 살아 있게 해 준다.
    DB에 없는 시험지만 넣으므로 여러 번 불러도 안전하다.
    """
    try:
        if not (DATA / "papers").exists():
            return 0
        import seed
        return seed.seed_missing(quiet=True)
    except Exception:
        return 0


def images(code: str, kind: str, no: int) -> List[bytes]:
    """kind: 'q'(문제) | 'a'(해설) | 'page'(문제 페이지 전체)"""
    rows = db().query("SELECT png FROM paper_files WHERE code=? AND kind=? AND no=? "
                      "ORDER BY idx", (code, kind, no))
    return [r["png"] for r in rows]


def page_images(code: str) -> List[bytes]:
    rows = db().query("SELECT png FROM paper_files WHERE code=? AND kind='page' "
                      "ORDER BY no", (code,))
    return [r["png"] for r in rows]


# ---------------------------------------------------------------- 정답 비교
_SUB = {
    "sqrt": "√", "root": "√", "루트": "√",
    "pi": "π", "파이": "π",
    "^2": "²", "^3": "³", "**2": "²", "**3": "³",
    "−": "-", "–": "-", "—": "-", "×": "*",
}


def normalize(s: Optional[str]) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", str(s)).strip().lower()
    for a, b in _SUB.items():
        s = s.replace(a, b)
    s = re.sub(r"(이다|입니다|이에요)\.?$", "", s)
    s = re.sub(r"[\s,'\"]+", "", s)
    return s


def judge(q: dict, given: Optional[str]) -> Optional[int]:
    """1=정답, 0=오답, None=자동채점 불가(선생님 확인).

    객관식은 번호 비교, 그 외에는
      ① 글자 그대로 같은가  ②  수학적으로 같은 값·같은 식인가 (mathcmp)
    순으로 본다. 둘 다 판단이 안 서면 선생님에게 넘긴다.
    """
    g = normalize(given)
    if g == "":
        return 0
    if q["qtype"] == "choice":
        return 1 if g == normalize(q["answer"]) else 0
    if g == normalize(q["answer"]):
        return 1
    import mathcmp
    r = mathcmp.equal(q["answer"], given)
    return None if r is None else (1 if r else 0)


def answer_hint(q: dict) -> str:
    """학생 입력칸에 띄울 안내 문구."""
    if q["qtype"] == "choice":
        return ""
    import mathcmp
    return mathcmp.hint(q["answer"])


# ---------------------------------------------------------------- 응시
def get_or_create_student(name: str, pin: str) -> Optional[dict]:
    d = db()
    name = name.strip()
    r = d.one("SELECT * FROM students WHERE name=?", (name,))
    if r:
        return r if r["pin"] == pin else None
    d.exec("INSERT INTO students(name,pin,created_at) VALUES(?,?,?)", (name, pin, now()))
    return d.one("SELECT * FROM students WHERE name=?", (name,))


def start_attempt(student_id: int, code: str, duration_min: int) -> int:
    started = datetime.now()
    return db().insert_id(
        "INSERT INTO attempts(student_id,paper_code,started_at,deadline,status) "
        "VALUES(?,?,?,?,'ongoing')",
        (student_id, code, started.isoformat(timespec="seconds"),
         (started + timedelta(minutes=duration_min)).isoformat(timespec="seconds")))


def ongoing_attempt(student_id: int) -> Optional[dict]:
    return db().one("SELECT * FROM attempts WHERE student_id=? AND status='ongoing' "
                    "ORDER BY id DESC LIMIT 1", (student_id,))


def save_response(attempt_id: int, no: int, answer: str):
    db().exec("INSERT INTO responses(attempt_id,no,answer) VALUES(?,?,?) "
              "ON CONFLICT(attempt_id,no) DO UPDATE SET answer=excluded.answer",
              (attempt_id, no, answer))


def get_responses(attempt_id: int) -> Dict[int, dict]:
    return {r["no"]: r for r in
            db().query("SELECT * FROM responses WHERE attempt_id=?", (attempt_id,))}


def grade_attempt(attempt_id: int, auto: bool = False) -> dict:
    d = db()
    a = d.one("SELECT * FROM attempts WHERE id=?", (attempt_id,))
    _, qs = load_paper(a["paper_code"])
    resp = get_responses(attempt_id)

    correct = gradable = 0
    pending, wrong = [], []
    for q in qs:
        given = resp[q["no"]]["answer"] if q["no"] in resp else ""
        v = judge(q, given)
        d.exec("INSERT INTO responses(attempt_id,no,answer,is_correct) VALUES(?,?,?,?) "
               "ON CONFLICT(attempt_id,no) DO UPDATE SET "
               "answer=excluded.answer, is_correct=excluded.is_correct",
               (attempt_id, q["no"], given, v))
        if v is None:
            pending.append(q["no"])
            continue
        gradable += 1
        if v == 1:
            correct += 1
            d.exec("UPDATE wrongnotes SET resolved_at=? WHERE student_id=? AND "
                   "paper_code=? AND no=? AND resolved_at IS NULL",
                   (now(), a["student_id"], a["paper_code"], q["no"]))
        else:
            wrong.append(q["no"])
            d.exec("INSERT INTO wrongnotes(student_id,paper_code,no,unit,created_at) "
                   "VALUES(?,?,?,?,?) ON CONFLICT(student_id,paper_code,no) "
                   "DO UPDATE SET resolved_at=NULL",
                   (a["student_id"], a["paper_code"], q["no"], q.get("unit") or "", now()))

    score = round(correct / gradable * 100, 1) if gradable else 0.0
    d.exec("UPDATE attempts SET submitted_at=?, status='done', score=?, total=?, "
           "auto_submitted=?, teacher_seen=0 WHERE id=?",
           (now(), score, gradable, 1 if auto else 0, attempt_id))
    return {"attempt_id": attempt_id, "score": score, "correct": correct,
            "gradable": gradable, "wrong": wrong, "pending": pending, "auto": auto}


def unit_stats(attempt_id: int) -> Dict[str, tuple]:
    a = db().one("SELECT * FROM attempts WHERE id=?", (attempt_id,))
    _, qs = load_paper(a["paper_code"])
    resp = get_responses(attempt_id)
    st: Dict[str, list] = {}
    for q in qs:
        r = resp.get(q["no"])
        if not r or r["is_correct"] is None:
            continue
        u = q.get("unit") or "미분류"
        st.setdefault(u, [0, 0])
        st[u][1] += 1
        st[u][0] += r["is_correct"]
    return {u: (v[0], v[1]) for u, v in sorted(st.items())}


def wrong_notes(student_id: int, only_open=True) -> List[dict]:
    q = ("SELECT * FROM wrongnotes WHERE student_id=?"
         + (" AND resolved_at IS NULL" if only_open else "")
         + " ORDER BY paper_code, no")
    return db().query(q, (student_id,))
