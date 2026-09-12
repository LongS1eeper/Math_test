"""클라우드 DB(Neon 등) 연결 점검. Neon 주소를 받은 직후 한 번 돌려 보세요.

    DATABASE_URL="postgresql://...?sslmode=require" python dbcheck.py

읽기·쓰기·이미지 저장·자동증가 id 까지 실제로 해 보고 흔적은 지웁니다.
"""
import os
import sys
import time

URL = os.environ.get("DATABASE_URL", "")
if not URL:
    print("DATABASE_URL 환경변수가 없습니다.")
    print('예)  DATABASE_URL="postgresql://user:pw@host/db?sslmode=require" python dbcheck.py')
    sys.exit(1)
if not URL.startswith(("postgres://", "postgresql://")):
    print(f"postgres 주소가 아닙니다: {URL[:30]}...")
    sys.exit(1)

try:
    import psycopg2  # noqa
except ImportError:
    print("psycopg2 가 없습니다.  pip install psycopg2-binary")
    sys.exit(1)

import core

t0 = time.time()
d = core.db(URL)
print(f"1. 접속 OK  ({core.db().kind}, {time.time()-t0:.1f}초)")

v = d.one("SELECT version() AS v")["v"]
print(f"2. 서버      {v.split(',')[0]}")

tables = d.query("SELECT table_name FROM information_schema.tables "
                 "WHERE table_schema='public' ORDER BY table_name")
print("3. 테이블    " + ", ".join(t["table_name"] for t in tables))

# 자동증가 id (RETURNING)
sid = d.insert_id("INSERT INTO students(name,pin,created_at) VALUES(?,?,?)",
                  ("__dbcheck__", "0000", core.now()))
print(f"4. id 자동증가 OK  (id={sid})")

# 이미지(BYTEA) 왕복
png = b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 40
core.put_paper({"code": "__DBCHECK__", "title": "점검", "duration_min": 1},
               [{"no": 1, "qtype": "choice", "answer": "3", "unit": "점검",
                 "needs_check": False, "n_choices": 5}],
               [("a", 1, 0, png)])
back = core.images("__DBCHECK__", "a", 1)[0]
assert back == png, "이미지 왕복 실패"
print(f"5. 이미지 저장·복원 OK  ({len(png)}바이트)")

# 채점 한 바퀴
aid = core.start_attempt(sid, "__DBCHECK__", 50)
core.save_response(aid, 1, "3")
r = core.grade_attempt(aid)
assert r["score"] == 100.0, r
print(f"6. 채점 OK  ({r['score']}점)")

# 정리
d.exec("DELETE FROM responses WHERE attempt_id=?", (aid,))
d.exec("DELETE FROM attempts WHERE id=?", (aid,))
d.exec("DELETE FROM wrongnotes WHERE student_id=?", (sid,))
d.exec("DELETE FROM students WHERE id=?", (sid,))
core.delete_paper("__DBCHECK__")
print("7. 정리 완료")
print(f"\n총 {time.time()-t0:.1f}초. 이 DB를 그대로 쓰시면 됩니다.")
print("다음:  DATABASE_URL=... python seed.py   ← 시험지를 클라우드로 올립니다")
