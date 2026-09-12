"""자동 추출이 안 된 주관식 정답을 채워 넣는다 (해설 이미지 확인 결과).

short = 자동채점 대상 / essay = 여러 값·식이라 선생님 확인 대상
"""
import json
from pathlib import Path

DATA = Path(__file__).parent / "data" / "papers"

FILL = {
    "Q1": {
        1:  ("short", "138"),
        6:  ("short", "(4,4)"),
        14: ("short", "16"),
        26: ("short", "100/3"),
    },
    "Q2": {
        10: ("short", "y=2x-5"),
        11: ("short", "(0,-2), (0,-10)"),
        18: ("short", "14"),
        19: ("short", "a=-1, b=-1, c=3"),
        20: ("essay", "y=mx±r√(m²+1)"),
        25: ("short", "(5+5√2)/2"),
        30: ("short", "2√7"),
    },
    "Q11": {
        2:  ("short", "a=8, b=3√5"),
        6:  ("short", "4"),
        10: ("short", "-10"),
        14: ("short", "(1) 17/2  (2) y=(3/4)x"),
        17: ("short", "37"),
        23: ("short", "(1) 6  (2) π"),
        27: ("short", "(12,5), (2,5), (4,-1), (-6,-1)"),
        31: ("short", "5"),
        32: ("short", "(x-4)²+(y-2)²=1"),
        33: ("short", "a=-2, b=-5, c=9"),
    },
    "Q12": {
        3:  ("short", "240"),
        8:  ("short", "27/2"),
        17: ("essay", "서술형 (풀이 과정 서술)"),
        19: ("short", "(1) AP:BP=1:2  (2) (x+2)²+y²=16"),
        21: ("short", "5√5"),
        26: ("short", "AB=2ar/k"),
        29: ("short", "-2"),
        30: ("short", "P=(3/4,3/4), Q=(12/7,12/7), min=5+√10"),
        33: ("short", "2√3"),
    },
}


def main():
    for code, fills in FILL.items():
        path = DATA / code / "answers.json"
        if not path.exists():
            print(f"skip {code}")
            continue
        qs = json.loads(path.read_text("utf-8"))
        for q in qs:
            if q["no"] in fills:
                qtype, ans = fills[q["no"]]
                q["qtype"] = qtype
                q["answer"] = ans
                q["needs_check"] = False
        path.write_text(json.dumps(qs, ensure_ascii=False, indent=2), "utf-8")
        left = [q["no"] for q in qs if q["needs_check"] or not q["answer"]]
        kinds = {}
        for q in qs:
            kinds[q["qtype"]] = kinds.get(q["qtype"], 0) + 1
        print(f"{code}: {kinds}  미완성={left or '없음'}")


if __name__ == "__main__":
    main()
