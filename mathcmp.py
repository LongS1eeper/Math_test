"""수학 답 비교기 — 표기가 달라도 같은 답이면 정답으로 인정한다. (외부 라이브러리 없음)

인정되는 것
    2√7   2root7   2sqrt7   2*sqrt(7)   sqrt(28)      → 모두 같은 값
    17/2  8.5                                          → 같은 값
    (4,4)  ( 4 , 4 )                                   → 좌표
    a=-1, b=-1, c=3   /  b=-1, a=-1, c=3               → 라벨은 순서 무관
    (12,5),(2,5),(4,-1),(-6,-1)                        → 좌표 묶음, 순서 무관
    y=2x-5   2x-y-5=0   -y+2x=5                        → 같은 직선
    (x-4)²+(y-2)²=1   x²+y²-8x-4y+19=0                 → 같은 원
    1:2   2:4                                          → 같은 비

판정 불가(선생님 확인으로 넘김)
    ± 가 들어간 답, 문장 서술, 우리가 못 읽는 표기
"""
from __future__ import annotations

import math
import random
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

TOL = 1e-7

FUNCS: Dict[str, Any] = {
    "sqrt": math.sqrt, "abs": abs,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "log": math.log, "exp": math.exp,
}
CONSTS: Dict[str, float] = {"pi": math.pi, "e": math.e}

_WORD_SUB = [
    ("루트", "sqrt"), ("root", "sqrt"), ("√", "sqrt"),
    ("파이", "pi"), ("π", "pi"),
    ("²", "^2"), ("³", "^3"), ("⁴", "^4"),
    ("−", "-"), ("–", "-"), ("—", "-"), ("×", "*"), ("÷", "/"),
    ("·", "*"), ("∙", "*"),
]

_TOKEN = re.compile(r"""
    (?P<num>\d+\.\d+|\d+)
  | (?P<id>[A-Za-z_]\w*)
  | (?P<op>\*\*|[-+*/^(),=:])
  | (?P<ws>\s+)
""", re.X)


# ------------------------------------------------------------------ 소스 변환
def _pre(s: str) -> str:
    # NFKC 는 위첨자 ²를 그냥 2로 바꿔 버린다. 치환을 먼저 한다.
    s = str(s)
    for a, b in _WORD_SUB:
        s = s.replace(a, b)
    return unicodedata.normalize("NFKC", s).strip()


_FUNC_JUX = re.compile(r"(?<![a-z])(" + "|".join(FUNCS) +
                       r")\s*(\d+(?:\.\d+)?|[a-z])(?![\w(])")


def _split_id(name: str) -> str:
    """모르는 여러 글자 변수는 곱으로 본다.  ar → a*r,  AB → a*b"""
    if name in FUNCS or name in CONSTS or len(name) == 1:
        return name
    return "*".join(name)


def to_source(s: str) -> Optional[str]:
    """사람이 쓴 수식 → 파이썬이 계산할 수 있는 문자열. 못 읽으면 None."""
    s = _pre(s).lower()
    if not s or "±" in s or "…" in s:
        return None
    if re.search(r"[가-힣]", s):            # 한글이 남아 있으면 서술형
        return None

    # √7 · sqrt7 · sqrt x  →  sqrt(7) · sqrt(x)
    for _ in range(4):
        s2 = _FUNC_JUX.sub(r"\1(\2)", s)
        if s2 == s:
            break
        s = s2

    toks: List[Tuple[str, str]] = []
    i = 0
    while i < len(s):
        m = _TOKEN.match(s, i)
        if not m:
            return None                      # 모르는 문자
        i = m.end()
        kind = m.lastgroup
        if kind != "ws":
            toks.append((kind, m.group()))
    if not toks:
        return None

    out: List[str] = []
    for j, (kind, val) in enumerate(toks):
        if out:
            pk, pv = toks[j - 1]
            prev_atom = pk in ("num", "id") or pv == ")"
            cur_atom = kind in ("num", "id") or val == "("
            func_call = pk == "id" and pv in FUNCS and val == "("
            if prev_atom and cur_atom and not func_call:
                out.append("*")
        out.append("**" if val == "^" else (_split_id(val) if kind == "id" else val))
    return "".join(out)


def free_vars(src: str) -> List[str]:
    ids = set(re.findall(r"[A-Za-z_]\w*", src))
    return sorted(ids - set(FUNCS) - set(CONSTS))


def evaluate(src: str, env: Optional[Dict[str, float]] = None) -> Optional[float]:
    g = {"__builtins__": {}}
    g.update(FUNCS)
    g.update(CONSTS)
    if env:
        g.update(env)
    if len(src) > 400 or "**" in src and re.search(r"\*\*\s*\d{4,}", src):
        return None                      # 터무니없는 거듭제곱 차단
    try:
        v = eval(src, g, {})            # noqa: S307 — 화이트리스트 전역만 노출
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return None
        v = float(v)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None


# ------------------------------------------------------------------ 답의 형태
class Ans:
    def __init__(self, kind: str, value: Any):
        self.kind = kind          # scalar | tuple | labeled | multi | relation | ratio
        self.value = value

    def __repr__(self):
        return f"Ans({self.kind}, {self.value!r})"


def _split_top(s: str, seps=",;") -> List[str]:
    """괄호 밖에서만 자른다."""
    out, buf, depth = [], "", 0
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch in seps and depth == 0:
            out.append(buf)
            buf = ""
        else:
            buf += ch
    out.append(buf)
    return [x.strip() for x in out if x.strip()]


_PART = re.compile(r"\(\s*(\d)\s*\)")         # (1) (2) 같은 소문항 표시


def _is_parts(raw: str) -> bool:
    """'(1) … (2) …' 처럼 소문항으로 나뉜 답인가.  sqrt(7) 의 (7) 과 구분한다."""
    ms = _PART.findall(raw)
    return (len(ms) >= 2 and raw.lstrip().startswith("(")
            and ms[0] == "1" and ms[1] == "2")


def parse(s: Optional[str]) -> Optional[Ans]:
    if s is None:
        return None
    raw = _pre(s)
    if not raw:
        return None

    # (1) ... (2) ... 소문항 → 순서 있는 묶음
    if _is_parts(raw):
        parts = [p.strip() for p in re.split(r"\(\s*\d\s*\)", raw) if p.strip()]
        subs = [parse(p) for p in parts]
        if len(subs) >= 2 and all(x is not None for x in subs):
            return Ans("multi", subs)
        return None

    chunks = _split_top(raw)
    if len(chunks) > 1:
        subs = [parse(c) for c in chunks]
        if all(x is not None for x in subs):
            if all(x.kind == "labeled" for x in subs):
                merged: Dict[str, Any] = {}
                for x in subs:
                    merged.update(x.value)
                return Ans("labeled", merged)
            return Ans("multi", subs)
        return None

    return _parse_one(raw)


_LABEL = re.compile(r"^([A-Za-z][A-Za-z0-9_']{0,3})\s*=\s*(.+)$")


def _parse_one(raw: str) -> Optional[Ans]:
    # 비  1:2
    if ":" in raw and "=" not in raw:
        parts = [evaluate(to_source(p) or "") for p in raw.split(":")]
        if len(parts) >= 2 and all(p is not None for p in parts):
            return Ans("ratio", _reduce(parts))
        return None

    # AP:BP = 1:2
    if ":" in raw and "=" in raw:
        lhs, rhs = raw.split("=", 1)
        r = _parse_one(rhs.strip())
        if r is not None and r.kind == "ratio":
            return Ans("labeled", {re.sub(r"\s+", "", lhs).lower(): r})
        return None

    if "=" in raw:
        lhs, rhs = raw.split("=", 1)
        sl, sr = to_source(lhs), to_source(rhs)
        m = _LABEL.match(raw)
        # 오른쪽이 상수이고 왼쪽이 이름 하나면 '라벨 = 값'  (a=8)
        if m and sr is not None and not free_vars(sr):
            inner = _parse_one(rhs.strip())
            if inner is not None and inner.kind in ("scalar", "tuple", "ratio"):
                return Ans("labeled", {m.group(1).lower(): inner})
        if not sl or not sr:
            return None
        src = f"({sl})-({sr})"
        if free_vars(src):                       # 변수가 있으면 방정식
            return Ans("relation", src)
        a, b = evaluate(sl), evaluate(sr)
        return Ans("scalar", a) if (a is not None and b is not None and
                                    abs(a - b) < TOL) else None

    # 좌표 (a, b)
    if raw.startswith("(") and raw.endswith(")"):
        inner = _split_top(raw[1:-1])
        if len(inner) >= 2:
            vals = [evaluate(to_source(x) or "") for x in inner]
            if all(v is not None for v in vals):
                return Ans("tuple", tuple(vals))
            return None

    src = to_source(raw)
    if not src:
        return None
    if free_vars(src):
        return Ans("expr", src)
    v = evaluate(src)
    return Ans("scalar", v) if v is not None else None


def _reduce(vals: List[float]) -> Tuple[float, ...]:
    base = next((v for v in vals if abs(v) > TOL), None)
    return tuple(vals) if base is None else tuple(v / base for v in vals)


# ------------------------------------------------------------------ 비교
_SAMPLES = [(1.7, 2.3), (-0.9, 3.1), (2.5, -1.4), (0.3, 0.8),
            (-2.2, -3.7), (4.1, 1.9), (1.1, -2.6), (3.3, 2.2)]


def _samples_for(names: List[str], n: int = 8) -> List[Dict[str, float]]:
    rnd = random.Random(20260912)
    out = []
    for k in range(n):
        env = {}
        for j, nm in enumerate(names):
            if k < len(_SAMPLES) and len(names) <= 2:
                env[nm] = _SAMPLES[k][j % 2]
            else:
                env[nm] = rnd.uniform(-4, 4)
        out.append(env)
    return out


def _expr_equal(s1: str, s2: str) -> bool:
    names = sorted(set(free_vars(s1)) | set(free_vars(s2)))
    if set(free_vars(s1)) != set(free_vars(s2)):
        return False
    for env in _samples_for(names):
        a, b = evaluate(s1, env), evaluate(s2, env)
        if a is None or b is None:
            return False
        if abs(a - b) > TOL * max(1.0, abs(a), abs(b)):
            return False
    return True


def _relation_equal(s1: str, s2: str) -> bool:
    """f1=0 과 f2=0 이 같은 도형인가 — f2 가 f1 의 0 아닌 상수배인지 본다."""
    names = sorted(set(free_vars(s1)) | set(free_vars(s2)))
    if not names:
        return False
    ratio = None
    checked = 0
    for env in _samples_for(names, 10):
        a, b = evaluate(s1, env), evaluate(s2, env)
        if a is None or b is None:
            return False
        if abs(a) < TOL and abs(b) < TOL:
            continue
        if abs(a) < TOL or abs(b) < TOL:
            return False
        r = b / a
        if ratio is None:
            ratio = r
        elif abs(r - ratio) > 1e-6 * max(1.0, abs(ratio)):
            return False
        checked += 1
    return checked >= 2 and ratio is not None


def _num_eq(a: float, b: float) -> bool:
    return abs(a - b) <= TOL * max(1.0, abs(a), abs(b))


def _unwrap1(a: Ans) -> Ans:
    """라벨이 하나뿐이면 알맹이만 꺼낸다.  {'y': 3} → 3"""
    if a.kind == "labeled" and len(a.value) == 1:
        return next(iter(a.value.values()))
    return a


def _eq(a: Ans, b: Ans) -> bool:
    if a.kind != b.kind:
        # 라벨을 생략하고 값만 쓴 경우도 인정한다:  'a=8' ↔ '8'
        ua, ub = _unwrap1(a), _unwrap1(b)
        if (ua is not a or ub is not b) and ua.kind == ub.kind:
            return _eq(ua, ub)
        # 'a=8, b=3√5'  ↔  '8, 3√5'  (적은 순서대로 맞춰 본다)
        for x, y in ((a, b), (b, a)):
            if x.kind == "labeled" and y.kind == "multi" and \
                    len(x.value) == len(y.value):
                return all(_eq(v, w) for v, w in zip(x.value.values(), y.value))
        return False
    if a.kind == "scalar":
        return _num_eq(a.value, b.value)
    if a.kind == "tuple":
        return len(a.value) == len(b.value) and \
            all(_num_eq(x, y) for x, y in zip(a.value, b.value))
    if a.kind == "ratio":
        return len(a.value) == len(b.value) and \
            all(_num_eq(x, y) for x, y in zip(a.value, b.value))
    if a.kind == "expr":
        return _expr_equal(a.value, b.value)
    if a.kind == "relation":
        return _relation_equal(a.value, b.value)
    if a.kind == "labeled":
        if set(a.value) != set(b.value):
            return False
        return all(_eq(a.value[k], b.value[k]) for k in a.value)
    if a.kind == "multi":
        if len(a.value) != len(b.value):
            return False
        if all(_eq(x, y) for x, y in zip(a.value, b.value)):
            return True
        # 순서 무관 비교 (좌표 묶음 등)
        pool = list(b.value)
        for x in a.value:
            hit = next((y for y in pool if _eq(x, y)), None)
            if hit is None:
                return False
            pool.remove(hit)
        return True
    return False


def equal(correct: str, given: str) -> Optional[bool]:
    """True=정답, False=오답, None=자동판정 불가(선생님 확인)."""
    if given is None or not str(given).strip():
        return False
    a = parse(correct)
    if a is None:
        return None                       # 정답 자체를 못 읽음 → 사람이 봐야 함
    b = parse(given)
    if b is None:
        return None                       # 학생 표기를 못 읽음 → 사람이 봐야 함
    return _eq(a, b)


# ------------------------------------------------------------------ 입력 안내
def hint(correct: str) -> str:
    """정답의 모양을 보고 학생에게 보여 줄 입력 예시를 만든다."""
    a = parse(correct)
    if a is None:
        return "답을 적어 주세요 (문장으로 써도 됩니다)"
    return _hint(a)


def _hint(a: Ans) -> str:
    if a.kind == "scalar":
        return "숫자로 입력 — 예) 138, 17/2, 2√7 (2root7 도 됩니다)"
    if a.kind == "tuple":
        n = len(a.value)
        return "좌표로 입력 — 예) (" + ", ".join(["3"] * n) + ")"
    if a.kind == "ratio":
        return "비로 입력 — 예) 1:2"
    if a.kind == "labeled":
        keys = ", ".join(f"{k}=…" for k in a.value)
        return f"각 값을 쉼표로 — 예) {keys}"
    if a.kind == "relation":
        return "식으로 입력 — 예) y=2x-5 (좌우변을 옮겨 써도 됩니다)"
    if a.kind == "expr":
        return "식으로 입력 — 예) 2ar/k"
    if a.kind == "multi":
        return "여러 답을 쉼표로 나눠서 — 순서는 상관없습니다"
    return "답을 입력하세요"
