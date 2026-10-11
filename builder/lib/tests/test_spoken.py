"""Spoken amounts, digit strings and dates in Turkish and English. Run: python builder/lib/tests/test_spoken.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from lib import spoken as s

NOW = "2026-10-14T11:00"   # a Wednesday
CASES = [
    ("amt", "dört yüz elli lira", 450.0), ("amt", "bin iki yüz", 1200.0), ("amt", "dört yüz elli virgül beş", 450.5),
    ("amt", "1.250,50 TL", 1250.5), ("amt", "450,50", 450.5), ("amt", "iki yüz elli buçuk", 250.5),
    ("amt", "four hundred and fifty-five", 455.0), ("amt", "twelve hundred", 1200.0), ("amt", "637.50", 637.5),
    ("amt", "2,125.10", 2125.1), ("amt", "dokuz yüz", 900.0),
    ("dig", "kırk dört yetmiş bir", "4471"), ("dig", "sıfır üç elli sekiz", "0358"), ("dig", "dört dört yedi bir", "4471"),
    ("dig", "44 71", "4471"), ("dig", "four four seven one", "4471"),
    ("date", "haftaya Cuma", "2026-10-23"), ("date", "bu Cuma", "2026-10-16"), ("date", "next Friday", "2026-10-23"),
    ("date", "this Friday", "2026-10-16"), ("date", "yarın", "2026-10-15"), ("date", "öbür gün", "2026-10-16"),
    ("date", "ayın on beşi", "2026-10-15"), ("date", "yirmi üç Ekim", "2026-10-23"), ("date", "15/10", "2026-10-15"),
    ("date", "10/15", "2026-10-15"), ("date", "the twenty-third of October", "2026-10-23"), ("date", "Cumartesi", "2026-10-17"),
    ("date", "Pazartesi", "2026-10-19"), ("date", "on üçü", "2026-11-13"), ("date", "the 30th", "2026-10-30"),
    ("dob", "on dört Mart seksen sekiz", "1988-03-14"), ("dob", "14 March 1988", "1988-03-14"), ("dob", "14.03.1988", "1988-03-14"),
    ("dob", "the fourteenth of March nineteen eighty-eight", "1988-03-14"),
    ("dob", "yirmi bir Temmuz bin dokuz yüz doksan iki", "1992-07-21"),
]


def main():
    fn = {"amt": s.parse_amount, "dig": s.parse_digits, "date": lambda t: s.parse_date(t, NOW), "dob": lambda t: s.parse_dob(t, NOW)}
    bad = [(k, t, fn[k](t), e) for k, t, e in CASES if fn[k](t) != e]
    for k, t, got, e in bad:
        print("FAIL", k, repr(t), "->", got, "expected", e)
    code = s.hook_source()
    assert "{{" not in code and "}}" not in code
    ns = {}
    exec(code, ns)                                   # the portable snippet runs on its own
    assert ns["parse_amount"]("dört yüz elli virgül beş") == 450.5
    print(f"{len(CASES) - len(bad)} / {len(CASES)} passed; hook snippet {len(code)} bytes")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
