"""streamlit 없이 DB·채점·알림 메시지를 검증한다.

    python test_core.py                                   # 로컬 SQLite
    DATABASE_URL=postgresql://... python test_core.py     # 클라우드 DB 점검
"""
import os
import sys

import core
import notify

FAIL = 0


def check(name, cond):
    global FAIL
    print(("  OK  " if cond else " FAIL ") + name)
    if not cond:
        FAIL += 1


def main():
    # ---- SQL 자리표시자 변환 (Postgres 경로의 핵심) ----
    check("? → %s 변환",
          core.to_pg("SELECT * FROM t WHERE a=? AND b=?")
          == "SELECT * FROM t WHERE a=%s AND b=%s")
    check("문자열 안의 ? 는 그대로",
          core.to_pg("SELECT '왜?' WHERE a=?") == "SELECT '왜?' WHERE a=%s")
    check("? 없는 문장은 무변화",
          core.to_pg("DELETE FROM t") == "DELETE FROM t")

    # ---- 정답 비교 ----
    for a, b in [("2√7", "2 root 7"), ("2√7", "2루트7"), ("100/3", " 100/3 "),
                 ("(4,4)", "(4, 4)"), ("y=2x-5", "Y = 2X - 5"), ("-10", "−10")]:
        check(f"정규화 {a!r} == {b!r}", core.normalize(a) == core.normalize(b))
    check("오답은 다르게 판정", core.normalize("138") != core.normalize("183"))

    # ---- DB ----
    d = core.db()
    print(f"\n  대상 DB: {d.kind}\n")
    papers = core.list_papers()
    check("시험지 등록됨", len(papers) > 0)
    if not papers:
        print("\n  → python seed.py 를 먼저 실행하세요.")
        sys.exit(1)

    for p in papers:
        code = p["code"]
        meta, qs = core.load_paper(code)
        blank = [q["no"] for q in qs if not str(q["answer"]).strip()]
        check(f'{code} 정답 누락 없음 {blank or ""}', not blank)
        bad = [q["no"] for q in qs if q["qtype"] == "choice"
               and str(q["answer"]) not in list("12345")]
        check(f'{code} 객관식 정답 형식 {bad or ""}', not bad)
        miss = [q["no"] for q in qs if not core.images(code, "a", q["no"])]
        check(f'{code} 해설 이미지 {miss or ""}', not miss)
        png = core.images(code, "a", qs[0]["no"])[0]
        check(f"{code} 이미지가 PNG 바이트", isinstance(png, bytes) and png[:4] == b"\x89PNG")

    # ---- 만점 / 영점 ----
    code = papers[0]["code"]
    meta, qs = core.load_paper(code)
    s = core.get_or_create_student("__selftest__", "0000")
    last = None
    for label, perfect in [("만점", True), ("영점", False)]:
        aid = core.start_attempt(s["id"], code, 50)
        for q in qs:
            core.save_response(aid, q["no"], q["answer"] if perfect else "___")
        r = core.grade_attempt(aid)
        check(f"{label} 시나리오 점수 {r['score']}",
              (r["score"] == 100.0) if perfect else (r["score"] == 0.0))
        last = r
    check("영점 뒤 오답노트 생성", len(core.wrong_notes(s["id"])) > 0)
    check("단원별 통계 계산", len(core.unit_stats(last["attempt_id"])) > 0)

    # ---- 정답표 전수 점검 ----
    import mathcmp
    unreadable, selffail = [], []
    auto = total = 0
    for p in papers:
        _, qs2 = core.load_paper(p["code"])
        for q in qs2:
            total += 1
            if q["qtype"] != "essay":
                auto += 1
            if q["qtype"] == "choice":
                continue
            if mathcmp.parse(q["answer"]) is None and q["qtype"] != "essay":
                unreadable.append((p["code"], q["no"], q["answer"]))
            elif core.judge(q, q["answer"]) not in (1, None):
                selffail.append((p["code"], q["no"], q["answer"]))
    check(f"정답을 그대로 적으면 모두 정답 처리 {selffail or ''}", not selffail)
    check(f"자동채점 대상 정답이 모두 읽힘 {unreadable or ''}", not unreadable)
    print(f"       → 총 {total}문항 중 자동채점 {auto}, 선생님 확인 {total - auto}")

    # ---- 학생이 다르게 적어도 인정되는가 ----
    variants = [
        ("2√7", "2root7", 1), ("2√7", "sqrt(28)", 1), ("2√7", "2√5", 0),
        ("y=2x-5", "2x-y-5=0", 1), ("y=2x-5", "y=2x+5", 0),
        ("(x-4)²+(y-2)²=1", "x^2+y^2-8x-4y+19=0", 1),
        ("(12,5), (2,5), (4,-1), (-6,-1)", "(2,5), (12,5), (-6,-1), (4,-1)", 1),
        ("a=-1, b=-1, c=3", "c=3, a=-1, b=-1", 1),
        ("17/2", "8.5", 1), ("100/3", "33.33", 0), ("138", "", 0),
    ]
    for ans, given, want in variants:
        got = core.judge({"qtype": "short", "answer": ans}, given)
        check(f"{ans!r} ← {given!r} = {'정답' if want else '오답'}", got == want)

    # ---- 알림 메시지 (발송 없이 문자열만) ----
    subj = notify.submission_subject("홍길동", meta["title"], last["score"])
    msg = notify.submission_body("홍길동", meta["title"], last,
                                 core.unit_stats(last["attempt_id"]),
                                 "https://example.com")
    check("알림 제목 생성", "홍길동" in subj and "점" in subj)
    check("알림 본문 생성", "홍길동" in msg and "틀린 문항" in msg)
    check("설정 없으면 채널 없음", isinstance(notify.channels(), list))
    ok, why = notify.send(subj, msg) if not notify.configured() else (None, "")
    check("설정 없이 보내면 조용히 실패", ok is False)
    check("알림 미설정이 채점을 막지 않음",
          notify.notify_submission(last["attempt_id"])[0] is False)
    print("\n--- 알림 미리보기 ---")
    print(subj)
    print(msg)
    print("---------------------\n")

    # ---- 시험지 zip 왕복 (GitHub 저장에 쓰는 형식) ----
    import gitstore
    import seed as seedmod
    blob = seedmod.make_zip(code)
    m2, q2, f2 = seedmod.load_zip(blob)
    om, oq, of = core.export_paper(code)
    check(f"zip 왕복 — 정답표 일치 ({len(blob)/1e6:.1f}MB)", q2 == oq)
    check("zip 왕복 — 이미지 수 일치", len(f2) == len(of))
    check("zip 왕복 — 이미지 바이트 일치",
          all(a[3] == b[3] for a, b in zip(sorted(f2), sorted(of))))
    check("zip 왕복 — 시험지 코드 유지", m2["code"] == om["code"])
    check("GitHub 미설정이면 configured=False", gitstore.configured() is False)
    ok, why = gitstore.check()
    check(f"GitHub 미설정 안내 문구 — {why}",
          ok is False and ("토큰" in why or "저장소" in why))
    check("빠진 시험지만 채우기(중복 없음)", seedmod.seed_missing() == 0)

    # ---- 정리 ----
    d.exec("DELETE FROM responses WHERE attempt_id IN "
           "(SELECT id FROM attempts WHERE student_id=?)", (s["id"],))
    d.exec("DELETE FROM attempts WHERE student_id=?", (s["id"],))
    d.exec("DELETE FROM wrongnotes WHERE student_id=?", (s["id"],))
    d.exec("DELETE FROM students WHERE id=?", (s["id"],))

    print("실패:", FAIL)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
