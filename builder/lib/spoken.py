"""Spoken numbers, amounts and dates (Turkish and English) -> canonical values. Standard library only.

Used two ways:
  * locally, to test and to precompute facts;
  * inside Freya hooks/code nodes: `hook_source()` returns this module's functions as one self-contained Python
    snippet (no imports beyond re/datetime, no '{{' or '}}'), so a pre-hook can coerce what the model sent.

    parse_amount("dört yüz elli virgül beş") -> 450.5      parse_amount("1.250,50 TL") -> 1250.5
    parse_digits("kırk dört yetmiş bir")      -> "4471"     parse_digits("sıfır üç elli sekiz") -> "0358"
    parse_date("haftaya Cuma", "2026-10-14T11:00") -> "2026-10-23"
    parse_dob("on dört Mart seksen sekiz")     -> "1988-03-14"
"""
import datetime
import re

# ---- BEGIN PORTABLE ----
_TR_UNITS = dict(sifir=0, bir=1, iki=2, uc=3, dort=4, bes=5, alti=6, yedi=7, sekiz=8, dokuz=9)
_TR_TENS = dict(on=10, yirmi=20, otuz=30, kirk=40, elli=50, altmis=60, yetmis=70, seksen=80, doksan=90)
_EN_UNITS = dict(zero=0, oh=0, one=1, two=2, three=3, four=4, five=5, six=6, seven=7, eight=8, nine=9, ten=10,
                 eleven=11, twelve=12, thirteen=13, fourteen=14, fifteen=15, sixteen=16, seventeen=17,
                 eighteen=18, nineteen=19)
_EN_TENS = dict(twenty=20, thirty=30, forty=40, fifty=50, sixty=60, seventy=70, eighty=80, ninety=90)
_SCALES = dict(yuz=100, hundred=100, bin=1000, thousand=1000, milyon=1000000, million=1000000)
_DEC = ("virgul", "nokta", "point")
_HALF = ("bucuk", "half")
_MONTHS = dict(ocak=1, subat=2, mart=3, nisan=4, mayis=5, haziran=6, temmuz=7, agustos=8, eylul=9, ekim=10,
               kasim=11, aralik=12, january=1, february=2, march=3, april=4, may=5, june=6, july=7, august=8,
               september=9, october=10, november=11, december=12, jan=1, feb=2, mar=3, apr=4, jun=6, jul=7,
               aug=8, sep=9, sept=9, oct=10, nov=11, dec=12)
_WEEKDAYS = dict(pazartesi=0, sali=1, carsamba=2, persembe=3, cuma=4, cumartesi=5, pazar=6, monday=0,
                 tuesday=1, wednesday=2, thursday=3, friday=4, saturday=5, sunday=6)
_ORD_EN = dict(first=1, second=2, third=3, fourth=4, fifth=5, sixth=6, seventh=7, eighth=8, ninth=9, tenth=10,
               eleventh=11, twelfth=12, thirteenth=13, fourteenth=14, fifteenth=15, sixteenth=16,
               seventeenth=17, eighteenth=18, nineteenth=19, twentieth=20, thirtieth=30)
_FOLD = str.maketrans("çğıöşüâîûÇĞİIÖŞÜ", "cgiosuaiucgiiosu")


def _fold(text):
    t = str(text or "").translate(_FOLD).lower()
    t = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", t)
    return t


def _strip_suffix(w):
    """Turkish case/possessive endings on number words: 'on besi', 'yirmisinde', 'onbeşinde' -> stem."""
    if w in _EN_UNITS or w in _EN_TENS or w in _ORD_EN or w in _TR_UNITS or w in _TR_TENS or w in _SCALES \
            or w in _MONTHS or w in _WEEKDAYS:
        return w
    for stem in sorted(list(_TR_UNITS) + list(_TR_TENS) + list(_SCALES) + list(_MONTHS) + list(_WEEKDAYS), key=len, reverse=True):
        if w.startswith(stem) and len(w) - len(stem) <= 5:
            return stem
    return w


def _tokens(text):
    t = _fold(text)
    t = t.replace("-", " ")
    return [w for w in re.split(r"[^a-z0-9.,]+", t) if w]


def _words_value(words):
    """A run of number words -> integer (handles 'iki yuz elli', 'bin iki yuz', 'four hundred and fifty five')."""
    total, cur, seen = 0, 0, False
    for w in words:
        w = _strip_suffix(w)
        if w in ("and", "ve"):
            continue
        if w in _TR_UNITS or w in _EN_UNITS:
            cur += _TR_UNITS.get(w, _EN_UNITS.get(w, 0))
            seen = True
        elif w in _TR_TENS or w in _EN_TENS:
            cur += _TR_TENS.get(w, _EN_TENS.get(w, 0))
            seen = True
        elif w in ("yuz", "hundred"):
            cur = (cur or 1) * 100
            seen = True
        elif w in ("bin", "thousand", "milyon", "million"):
            total += (cur or 1) * _SCALES[w]
            cur = 0
            seen = True
        elif w.isdigit():
            cur += int(w)
            seen = True
        else:
            return None
    return total + cur if seen else None


def _is_num_word(w):
    w = _strip_suffix(w)
    return w in _TR_UNITS or w in _TR_TENS or w in _EN_UNITS or w in _EN_TENS or w in _SCALES or w in ("ve", "and")


def parse_amount(text):
    """Spoken or written amount -> float, or None. Turkish decimal comma and dot thousands are handled."""
    raw = str(text or "").strip()
    m = re.search(r"\d[\d.,\s]*", raw)
    if m and not re.search(r"[a-zA-Zçğıöşü]{3,}\s*\d", raw):
        s = m.group(0).replace(" ", "").rstrip(".,")
        if re.search(r",\d{1,2}$", s):                     # 1.250,50 or 450,5 -> decimal comma
            s = s.replace(".", "").replace(",", ".")
        elif re.search(r"\.\d{1,2}$", s) and s.count(".") == 1:   # 450.50 -> decimal point
            s = s.replace(",", "")
        else:                                              # 1.250 or 1,250 -> thousands separators
            s = s.replace(".", "").replace(",", "")
        try:
            return round(float(s), 2)
        except ValueError:
            return None
    toks = [w for w in _tokens(raw) if w not in ("lira", "tl", "kurus", "dollars", "dollar", "euro", "euros", "pounds")]
    whole, frac, half, mode = [], [], False, "whole"
    for w in toks:
        if w in _DEC:
            mode = "frac"
        elif w in _HALF:
            half = True
        elif _is_num_word(w) or w.isdigit():
            (whole if mode == "whole" else frac).append(w)
    v = _words_value(whole) if whole else None
    if v is None:
        return None
    if frac:
        digits = "".join(str(_words_value([f]) or 0) if _strip_suffix(f) in ("sifir", "zero", "oh") else str(_words_value([f]) or "")
                         for f in frac)
        f = _words_value(frac)
        if f is not None:
            digits = ("0" if frac and _strip_suffix(frac[0]) in ("sifir", "zero", "oh") else "") + str(f)
            v = float(f"{v}.{digits}")
    if half:
        v = v + 0.5
    return round(float(v), 2)


def parse_digits(text):
    """Digit-string answers (last four digits, codes): '44 71', 'kirk dort yetmis bir', 'sifir uc elli sekiz'.
    Each spoken group is written out in full and the groups are concatenated; leading zeros are kept."""
    raw = str(text or "")
    if re.fullmatch(r"[\d\s\-.]+", raw.strip()):
        return re.sub(r"\D", "", raw)
    out, group = [], []

    def flush():
        if group:
            v = _words_value(group)
            if v is not None:
                out.append(str(v))
            group.clear()

    for w in _tokens(raw):
        s = _strip_suffix(w)
        if w.isdigit():
            flush()
            out.append(w)
        elif s in ("sifir", "zero", "oh"):
            flush()
            out.append("0")
        elif s in _TR_UNITS or s in _EN_UNITS:
            group.append(w)
            flush()
        elif s in _TR_TENS or s in _EN_TENS:
            flush()
            group.append(w)
        elif s in _SCALES:
            group.append(w)
        else:
            flush()
    flush()
    return "".join(out)


def _year(y, today):
    y = int(y)
    if y < 100:
        y += 2000 if y <= today.year % 100 else 1900
    return y


def _to_date(now):
    s = str(now or "")[:10]
    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        return datetime.date.today()


def parse_date(text, now, order="DMY"):
    """Spoken/written date relative to `now` (ISO) -> 'YYYY-MM-DD' or None. Weekday rules: 'this X' = X in the
    current week; 'next X' / 'haftaya X' / 'gelecek hafta X' = X in the following calendar week; a bare weekday
    = the next X on or after today. 'the 15th' / 'ayin on besi' = the 15th of this month, or next month if past."""
    today = _to_date(now)
    t = _fold(text)
    words = _tokens(text)
    if re.search(r"\b(bugun|today)\b", t):
        return today.isoformat()
    if re.search(r"\b(obur gun|ertesi gun|day after tomorrow)\b", t):
        return (today + datetime.timedelta(days=2)).isoformat()
    if re.search(r"\b(yarin|tomorrow)\b", t):
        return (today + datetime.timedelta(days=1)).isoformat()
    m = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", t)
    if m:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
    m = re.search(r"\b(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?\b", t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        d, mo = (a, b) if order == "DMY" else (b, a)
        if mo > 12 and d <= 12:
            d, mo = mo, d
        y = _year(m.group(3), today) if m.group(3) else today.year
        try:
            return datetime.date(y, mo, d).isoformat()
        except ValueError:
            return None
    wd = next((_WEEKDAYS[_strip_suffix(w)] for w in words if _strip_suffix(w) in _WEEKDAYS
               and not (_strip_suffix(w) == "pazar" and "pazartesi" in w)), None)
    for w in words:                                   # 'cumartesi' must not read as 'cuma'
        s = _strip_suffix(w)
        if s in _WEEKDAYS and w.startswith(("cumartesi", "pazartesi")):
            wd = _WEEKDAYS["cumartesi" if w.startswith("cumartesi") else "pazartesi"]
    month = next((_MONTHS[_strip_suffix(w)] for w in words if _strip_suffix(w) in _MONTHS), None)
    if month is None and wd is not None:
        monday = today - datetime.timedelta(days=today.weekday())
        if re.search(r"\b(next|haftaya|gelecek hafta|onumuzdeki hafta|ertesi hafta)\b", t):
            return (monday + datetime.timedelta(days=7 + wd)).isoformat()
        if re.search(r"\b(this|bu)\b", t):
            return (monday + datetime.timedelta(days=wd)).isoformat()
        delta = (wd - today.weekday()) % 7
        return (today + datetime.timedelta(days=delta)).isoformat()
    # day number: digits, ordinals or number words
    day = None
    for w in words:
        if w.isdigit() and 1 <= int(w) <= 31 and day is None:
            day = int(w)
    if day is None:
        for w in words:
            if w in _ORD_EN:
                day = _ORD_EN[w] if day is None else day
        if day is None:
            run = [w for w in words if _is_num_word(w) and _strip_suffix(w) not in ("yuz", "bin", "hundred", "thousand")]
            if run:
                v = _words_value(run[:2])
                if v and 1 <= v <= 31:
                    day = v
        else:
            m2 = re.search(r"(twenty|thirty)[ -](first|second|third|fourth|fifth|sixth|seventh|eighth|ninth)", t)
            if m2:
                day = _EN_TENS[m2.group(1)] + _ORD_EN[m2.group(2)]
    if day is None:
        return None
    y = today.year
    ym = re.search(r"\b(\d{4})\b", t)
    if ym:
        y = int(ym.group(1))
    if month is None:
        month = today.month
        try:
            cand = datetime.date(y, month, day)
        except ValueError:
            return None
        if cand < today:
            month = 1 if today.month == 12 else today.month + 1
            y = y + 1 if today.month == 12 else y
    try:
        return datetime.date(y, month, day).isoformat()
    except ValueError:
        return None


def parse_dob(text, now=None):
    """Date of birth in words or digits -> 'YYYY-MM-DD' (day-month-year order for digits)."""
    today = _to_date(now)
    t = _fold(text)
    m = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", t)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"\b(\d{1,2})[./ ](\d{1,2})[./ ](\d{2,4})\b", t)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), _year(m.group(3), today)
        if mo > 12 and d <= 12:
            d, mo = mo, d
        return f"{y:04d}-{mo:02d}-{d:02d}"
    words = _tokens(text)
    mi = next((i for i, w in enumerate(words) if _strip_suffix(w) in _MONTHS), None)
    if mi is None:
        return None
    month = _MONTHS[_strip_suffix(words[mi])]
    before = [w for w in words[:mi] if _is_num_word(w) or w.isdigit() or w in _ORD_EN]
    after = [w for w in words[mi + 1:] if _is_num_word(w) or w.isdigit()]
    day = None
    if before:
        day = _ORD_EN.get(before[-1]) or _words_value([w for w in before if w not in _ORD_EN][-2:])
        if before and before[-1] in _ORD_EN and len(before) > 1 and before[-2] in _EN_TENS:
            day = _EN_TENS[before[-2]] + _ORD_EN[before[-1]]
    if not after:
        return None
    if len(after) == 1 and after[0].isdigit():
        year = _year(after[0], today)
    else:
        yv = _words_value(after)
        if yv is None:
            return None
        if yv < 100:
            year = _year(yv, today)
        elif yv < 1000:                                  # 'nineteen eighty-eight' read as 19 + 88
            year = yv
        else:
            year = yv
        if len(after) >= 2 and _strip_suffix(after[0]) in ("nineteen",) and yv < 1000:
            year = 1900 + _words_value(after[1:])
    if not day or not (1 <= day <= 31):
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"
# ---- END PORTABLE ----


def hook_source():
    """The portable part of this module as a Python snippet for Freya hooks / code nodes."""
    import inspect, sys
    src = inspect.getsource(sys.modules[__name__])
    body = src.split("# ---- BEGIN PORTABLE ----", 1)[1].split("# ---- END PORTABLE ----", 1)[0]
    code = "import re\nimport datetime\n" + body
    assert "{{" not in code and "}}" not in code
    compile(code, "spoken", "exec")
    return code
