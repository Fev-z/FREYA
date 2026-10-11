"""Deterministic calendar / amount / identity rules, parameterized by a spec dict.

Everything between the PORTABLE markers is also embedded verbatim (indented inside
one wrapper function) into Freya code_exec snippets and api_call hooks by codegen.py.
So that region must:
  * use only json / re / datetime (imported by the wrapper),
  * never contain two consecutive curly braces (open or close),
  * never rely on module globals other than those three modules.
See spec_schema.md for the spec fields.
"""
import datetime
import json
import re

# ---- BEGIN PORTABLE ----
WEEKDAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
               'August', 'September', 'October', 'November', 'December']


def to_date(x):
    """Accept date, datetime or 'YYYY-MM-DD...' string. Return datetime.date or None."""
    if isinstance(x, datetime.datetime):
        return x.date()
    if isinstance(x, datetime.date):
        return x
    s = str(x or '').strip()
    m = re.match(r'^(\d\d\d\d)-(\d\d?)-(\d\d?)', s)
    if not m:
        return None
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except Exception:
        return None


def to_datetime(x):
    """Parse 'YYYY-MM-DDTHH:MM[:SS]' (or a date) into datetime.datetime, or None."""
    if isinstance(x, datetime.datetime):
        return x
    d = to_date(x)
    if d is None:
        return None
    s = str(x or '')
    m = re.search(r'[T ](\d\d?):(\d\d)', s)
    hh, mm = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
    return datetime.datetime(d.year, d.month, d.day, hh, mm)


def to_float(x):
    try:
        if isinstance(x, (int, float)):
            return float(x)
        s = re.sub(r'[^0-9.\-]', '', str(x).replace(',', ''))
        return float(s) if s not in ('', '-', '.') else None
    except Exception:
        return None


def hhmm_to_minutes(s):
    m = re.match(r'^\s*(\d\d?)[:.h]?(\d\d)?', str(s or ''))
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2) or 0)


def weekday_index(name_or_int):
    if isinstance(name_or_int, int):
        return name_or_int % 7
    s = str(name_or_int).strip().lower()[:3]
    for i, n in enumerate(WEEKDAY_NAMES):
        if n.lower()[:3] == s:
            return i
    return None


def weekend_set(spec):
    raw = spec.get('weekend_days')
    if raw is None:
        raw = [5, 6]
    out = set()
    for w in raw:
        i = weekday_index(w)
        if i is not None:
            out.add(i)
    return out


def holiday_set(spec):
    out = set()
    for h in spec.get('holidays') or []:
        d = to_date(h.get('date') if isinstance(h, dict) else h)
        if d is not None:
            out.add(d.isoformat())
    return out


def is_business_day(d, spec):
    d = to_date(d)
    if d is None:
        return False
    return d.weekday() not in weekend_set(spec) and d.isoformat() not in holiday_set(spec)


def non_business_reason(d, spec):
    d = to_date(d)
    if d.isoformat() in holiday_set(spec):
        return 'bank holiday'
    if d.weekday() in weekend_set(spec):
        return 'weekend'
    return ''


def next_business_day_on_or_after(d, spec):
    d = to_date(d)
    for _ in range(400):
        if is_business_day(d, spec):
            return d
        d = d + datetime.timedelta(days=1)
    return d


def previous_business_day_on_or_before(d, spec):
    d = to_date(d)
    for _ in range(400):
        if is_business_day(d, spec):
            return d
        d = d - datetime.timedelta(days=1)
    return d


def add_business_days(d, n, spec):
    """The n-th business day strictly after d (n >= 1). n == 0: d itself if business day, else next."""
    d = to_date(d)
    n = int(n)
    if n <= 0:
        return next_business_day_on_or_after(d, spec)
    count = 0
    for _ in range(4000):
        d = d + datetime.timedelta(days=1)
        if is_business_day(d, spec):
            count += 1
            if count >= n:
                return d
    return d


def week_start(d, spec):
    d = to_date(d)
    ws = weekday_index(spec.get('week_start_day', 0))
    ws = 0 if ws is None else ws
    return d - datetime.timedelta(days=(d.weekday() - ws) % 7)


def last_business_day_of_week(d, spec, weeks_ahead=0):
    """Latest business day of the calendar week containing d (weeks_ahead=1: next week). None if none."""
    start = week_start(d, spec) + datetime.timedelta(days=7 * int(weeks_ahead))
    for k in range(6, -1, -1):
        c = start + datetime.timedelta(days=k)
        if is_business_day(c, spec):
            return c
    return None


def resolve_weekday(kind, weekday, today, spec):
    """kind 'this' | 'next'. Convention from spec['weekday_convention'] (see spec_schema.md)."""
    today = to_date(today)
    wd = weekday_index(weekday)
    conv = spec.get('weekday_convention') or dict()
    if kind == 'this':
        rule = conv.get('this', 'current_week')
        if rule == 'next_occurrence_inclusive':
            return today + datetime.timedelta(days=(wd - today.weekday()) % 7)
        return week_start(today, spec) + datetime.timedelta(days=(wd - week_start(today, spec).weekday()) % 7)
    rule = conv.get('next', 'following_week')
    if rule == 'next_occurrence':
        delta = (wd - today.weekday()) % 7
        return today + datetime.timedelta(days=delta if delta else 7)
    if rule == 'occurrence_after_next':
        delta = (wd - today.weekday()) % 7
        return today + datetime.timedelta(days=(delta if delta else 7) + 7)
    nxt = week_start(today, spec) + datetime.timedelta(days=7)
    return nxt + datetime.timedelta(days=(wd - nxt.weekday()) % 7)


def band_for(days_late, spec, product_type=None):
    """Return the band dict whose [min_days_late, max_days_late] holds days_late (closest band if none)."""
    bands = [b for b in (spec.get('bands') or []) if isinstance(b, dict)]
    if product_type:
        typed = [b for b in bands if b.get('product_types') and product_type in b.get('product_types')]
        untyped = [b for b in bands if not b.get('product_types')]
        bands = typed + untyped if typed else untyped or bands
    dl = to_float(days_late)
    if dl is None or not bands:
        return bands[0] if bands else None
    for b in bands:
        lo = to_float(b.get('min_days_late'))
        hi = to_float(b.get('max_days_late'))
        if (lo is None or dl >= lo) and (hi is None or dl <= hi):
            return b
    best, dist = None, None
    for b in bands:
        lo = to_float(b.get('min_days_late'))
        hi = to_float(b.get('max_days_late'))
        dd = (lo - dl) if (lo is not None and dl < lo) else ((dl - hi) if hi is not None else 0)
        if dist is None or dd < dist:
            best, dist = b, dd
    return best


def deadline_from_band(band, today, spec):
    today = to_date(today)
    if not band:
        return None
    unit = band.get('deadline_unit', 'business_days')
    n = int(to_float(band.get('deadline_count')) or 0)
    if unit == 'business_days':
        raw = add_business_days(today, n, spec)
    elif unit == 'calendar_days':
        raw = today + datetime.timedelta(days=n)
    elif unit == 'end_of_week':
        raw = week_start(today, spec) + datetime.timedelta(days=6 + 7 * n)
    elif unit == 'end_of_month':
        y, m = today.year, today.month + n
        while m > 12:
            y, m = y + 1, m - 12
        nm = datetime.date(y + (1 if m == 12 else 0), 1 if m == 12 else m + 1, 1)
        raw = nm - datetime.timedelta(days=1)
    elif unit == 'fixed_date':
        raw = to_date(band.get('deadline_date')) or today
    else:
        raw = add_business_days(today, n, spec)
    roll = band.get('deadline_roll', spec.get('deadline_roll', 'previous_business_day'))
    if roll == 'next_business_day':
        return next_business_day_on_or_after(raw, spec)
    if roll == 'none':
        return raw
    return previous_business_day_on_or_before(raw, spec)


def deadline_for(product, now, spec):
    """Latest allowed promise date (datetime.date) for one product dict."""
    product = product or dict()
    band = band_for(product.get('days_late'), spec, product.get('type'))
    return deadline_from_band(band, to_date(now), spec)


def floor_for(product, spec):
    """Minimum acceptable amount for a product (float) or None."""
    product = product or dict()
    ptype = product.get('type')
    fields = spec.get('floor_field_by_product_type') or dict()
    field = fields.get(ptype) or spec.get('floor_field_default')
    if field and to_float(product.get(field)) is not None:
        return round(to_float(product.get(field)), 2)
    pct = (spec.get('floor_percent_by_product_type') or dict()).get(ptype, spec.get('floor_percent_default'))
    if pct is not None and to_float(product.get('past_due')) is not None:
        return round(to_float(product.get('past_due')) * to_float(pct) / 100.0, 2)
    return None


def attempts_for(product, spec):
    product = product or dict()
    band = band_for(product.get('days_late'), spec, product.get('type')) or dict()
    return int(to_float(band.get('attempts')) or 0)


def earliest_promise_date(now, spec):
    today = to_date(now)
    off = int(to_float(spec.get('promise_min_offset_days')) or 0)
    d = today + datetime.timedelta(days=off)
    if spec.get('promise_business_day_only', True):
        d = next_business_day_on_or_after(d, spec)
    return d


def default_proposal_date(now, spec):
    """Date for persuasion attempt 1 (spec['proposal_date_rule'])."""
    today = to_date(now)
    rule = spec.get('proposal_date_rule', 'last_business_day_of_week')
    if rule == 'next_business_day':
        return add_business_days(today, 1, spec)
    if rule == 'today':
        return next_business_day_on_or_after(today, spec)
    d = last_business_day_of_week(today, spec, 0)
    if d is None or d <= today:
        d = last_business_day_of_week(today, spec, 1)
    return d


def product_label(product, spec):
    product = product or dict()
    tmpl = (spec.get('product_labels') or dict()).get(product.get('type'))
    if not tmpl:
        tmpl = str(product.get('type') or 'product').replace('_', ' ')
    out = str(tmpl)
    for k, v in product.items():
        out = out.replace('<' + str(k) + '>', str(v))
    return out


def spoken_date(d):
    d = to_date(d)
    if d is None:
        return ''
    return WEEKDAY_NAMES[d.weekday()] + ' ' + str(d.day) + ' ' + MONTH_NAMES[d.month - 1] + ' ' + str(d.year)


def fmt_amount(x):
    x = to_float(x)
    return '' if x is None else ('%.2f' % x)


def promise_check(product, date, amount, now, spec):
    """Validate one promise. Returns dict(ok, reason, suggest_date, suggest_amount, message)."""
    product = product or dict()
    today = to_date(now)
    out = dict(ok=False, reason='', suggest_date='', suggest_amount='', message='')
    d = to_date(date)
    dl = deadline_for(product, today, spec)
    full = to_float(product.get('past_due'))
    fl = floor_for(product, spec)
    a = to_float(amount)
    if d is None:
        out.update(reason='bad_date', suggest_date=dl.isoformat() if dl else '',
                   message='Ask for an exact calendar day.')
        return out
    earliest = earliest_promise_date(today, spec)
    if d < today or (d < earliest and spec.get('promise_min_offset_days')):
        out.update(reason='before_earliest', suggest_date=earliest.isoformat(),
                   message='Date is too early. Earliest allowed: ' + spoken_date(earliest) + '.')
        return out
    if dl is not None and d > dl:
        out.update(reason='after_deadline', suggest_date=dl.isoformat(),
                   message='Date is after the deadline. Latest date you can record: ' + spoken_date(dl) + '.')
        return out
    if spec.get('promise_business_day_only', True) and not is_business_day(d, spec):
        nb = next_business_day_on_or_after(d, spec)
        if dl is not None and nb > dl:
            nb = dl
        out.update(reason='not_business_day', suggest_date=nb.isoformat(),
                   message=spoken_date(d) + ' is not a business day (' + non_business_reason(d, spec)
                   + '). Offer ' + spoken_date(nb) + '.')
        return out
    if a is None:
        out.update(reason='bad_amount', suggest_amount=fmt_amount(full), message='Propose the full amount.')
        return out
    if full is not None and a > full + 0.005:
        out.update(reason='above_full', suggest_amount=fmt_amount(full),
                   message='Amount is above the past-due amount ' + fmt_amount(full) + '.')
        return out
    if fl is not None and a < fl - 0.005:
        out.update(reason='below_floor', suggest_amount=fmt_amount(fl),
                   message='Amount is below the floor. It cannot be recorded. Offer ' + fmt_amount(fl) + ' once.')
        return out
    out.update(ok=True, reason='ok', suggest_date=d.isoformat(), suggest_amount=fmt_amount(a),
               message='Promise is valid: ' + fmt_amount(a) + ' on ' + spoken_date(d) + '.')
    return out


def callback_allowed_dates(now, spec):
    cb = spec.get('callback') or dict()
    today = to_date(now)
    out = []
    for key in cb.get('allowed_days') or ['today', 'next_business_day']:
        if key == 'today':
            if not cb.get('business_days_only') or is_business_day(today, spec):
                out.append(today)
        elif key == 'next_business_day':
            out.append(add_business_days(today, 1, spec))
        elif key == 'tomorrow':
            out.append(today + datetime.timedelta(days=1))
        else:
            m = re.match(r'^next_(\d+)_business_days$', str(key))
            if m:
                for i in range(1, int(m.group(1)) + 1):
                    out.append(add_business_days(today, i, spec))
    return sorted(set(out))


def callback_slot_valid(date, time, now, spec):
    """Check a callback slot. Returns dict(ok, reason, allowed_dates)."""
    cb = spec.get('callback') or dict()
    nowdt = to_datetime(now)
    d = to_date(date)
    t = hhmm_to_minutes(time)
    allowed = callback_allowed_dates(nowdt, spec)
    res = dict(ok=False, reason='', allowed_dates=[x.isoformat() for x in allowed])
    if d is None or t is None:
        res['reason'] = 'unreadable'
        return res
    if d not in allowed:
        res['reason'] = 'day_not_allowed'
        return res
    lo = hhmm_to_minutes(cb.get('start', '00:00'))
    hi = hhmm_to_minutes(cb.get('end', '23:59'))
    if t < lo or t > hi:
        res['reason'] = 'time_outside_window'
        return res
    if cb.get('must_be_after_now', True) and nowdt is not None:
        slot = datetime.datetime(d.year, d.month, d.day, t // 60, t % 60)
        if slot <= nowdt:
            res['reason'] = 'not_after_now'
            return res
    res.update(ok=True, reason='ok')
    return res


def normalize_date_answer(s, order='DMY'):
    """Turn a spoken / typed date into YYYY-MM-DD. Digits-only dates read in `order`. Returns input if unreadable."""
    raw = str(s or '').strip()
    if re.match(r'^\d\d\d\d-\d\d-\d\d$', raw):
        return raw
    low = raw.lower()
    month = None
    for i, n in enumerate(MONTH_NAMES):
        if re.search(r'\b' + n.lower()[:3], low):
            month = i + 1
            break
    nums = [int(x) for x in re.findall(r'\d+', low)]
    year, day = None, None
    if month is not None:
        for x in nums:
            if x > 31 and year is None:
                year = x
            elif day is None and 1 <= x <= 31:
                day = x
        if year is None and len(nums) >= 2:
            year = nums[-1]
    elif len(nums) >= 3:
        if nums[0] > 31:
            year, month, day = nums[0], nums[1], nums[2]
        elif str(order).upper() == 'MDY':
            month, day, year = nums[0], nums[1], nums[2]
        else:
            day, month, year = nums[0], nums[1], nums[2]
        if month > 12 and day <= 12:
            day, month = month, day
    if year is None or month is None or day is None:
        return raw
    if year < 100:
        year += 1900 if year > 30 else 2000
    try:
        return datetime.date(year, month, day).isoformat()
    except Exception:
        return raw


def _maybe_json(x):
    if isinstance(x, str):
        s = x.strip()
        if s[:1] in ('[', '{'):
            try:
                return json.loads(s)
            except Exception:
                try:
                    return json.loads(s.replace("'", '"').replace('True', 'true').replace('False', 'false').replace('None', 'null'))
                except Exception:
                    return x
    return x


def read_products(v, spec):
    """Find the products list in vars: mapped var, JSON string, envelope, or flattened keys."""
    names = list(spec.get('products_var_names') or []) + ['products', 'accounts', 'account',
                                                         'get_account_response.data.products',
                                                         'get_account_response.data', 'get_account_response']
    for name in names:
        x = _maybe_json(v.get(name))
        if isinstance(x, dict):
            x = _maybe_json(x.get('data', x))
            if isinstance(x, dict):
                x = _maybe_json(x.get('products'))
        if isinstance(x, list) and x and isinstance(x[0], dict):
            return x
    prefix_list = [p + '.' for p in names if p.endswith('products')] + ['get_account_response.data.products.']
    items = dict()
    for k in list(v.keys()):
        ks = str(k)
        for pre in prefix_list:
            if ks.startswith(pre):
                rest = ks[len(pre):]
                m = re.match(r'^\[?(\d+)\]?\.(.+)$', rest)
                if m:
                    items.setdefault(int(m.group(1)), dict())[m.group(2)] = v.get(k)
    return [items[i] for i in sorted(items)]


def compute_all(v, spec):
    """Write every derived fact into v (vars) as strings. Never raises."""
    nowdt = to_datetime(v.get('now')) or datetime.datetime.now()
    today = nowdt.date()
    products = []
    try:
        products = read_products(v, spec)
    except Exception:
        products = []
    v['today'] = today.isoformat()
    v['today_spoken'] = spoken_date(today)
    v['n_products'] = str(len(products))
    p1 = default_proposal_date(today, spec)
    v['attempt1_date'] = p1.isoformat() if p1 else ''
    lines = []
    prod_lines = []
    deadlines = []
    for i, p in enumerate(products):
        k = 'p' + str(i + 1) + '_'
        band = band_for(p.get('days_late'), spec, p.get('type')) or dict()
        dl = deadline_from_band(band, today, spec)
        fl = floor_for(p, spec)
        att = int(to_float(band.get('attempts')) or 0)
        a1 = p1 if (p1 and dl and p1 <= dl) else dl
        v[k + 'id'] = str(p.get('product_id') or ('p' + str(i + 1)))
        v[k + 'type'] = str(p.get('type') or '')
        v[k + 'label'] = product_label(p, spec)
        v[k + 'past_due'] = fmt_amount(p.get('past_due'))
        v[k + 'days_late'] = str(p.get('days_late') if p.get('days_late') is not None else '')
        v[k + 'band'] = str(band.get('name') or '')
        v[k + 'deadline'] = dl.isoformat() if dl else ''
        v[k + 'deadline_spoken'] = spoken_date(dl) if dl else ''
        v[k + 'floor'] = fmt_amount(fl)
        v[k + 'attempts'] = str(att)
        v[k + 'attempt1_date'] = a1.isoformat() if a1 else ''
        deadlines.append((v[k + 'id'], v[k + 'label'], dl))
        prod_lines.append('- ' + v[k + 'id'] + ' (' + v[k + 'label'] + '): past due ' + v[k + 'past_due']
                          + ', ' + v[k + 'days_late'] + ' days late, band ' + v[k + 'band']
                          + ', floor ' + (v[k + 'floor'] or 'none') + ', persuasion attempts ' + str(att)
                          + ', LATEST promise date ' + v[k + 'deadline_spoken'] + ' (' + v[k + 'deadline'] + ')'
                          + ', attempt-1 date ' + spoken_date(a1) + ' (' + v[k + 'attempt1_date'] + ')')
    if products:
        for key in ('id', 'label', 'past_due', 'days_late', 'band', 'deadline', 'deadline_spoken', 'floor',
                    'attempts', 'attempt1_date'):
            v[key if key != 'id' else 'product_id'] = v.get('p1_' + key, '')
    v['product_facts'] = '\n'.join(prod_lines) if prod_lines else 'Products not loaded yet.'
    lines.append('TODAY is ' + spoken_date(today) + ' (' + today.isoformat() + '), time now '
                 + nowdt.strftime('%H:%M') + '.')
    hol = sorted(holiday_set(spec))
    lines.append('Business days: ' + ', '.join(WEEKDAY_NAMES[i] for i in range(7) if i not in weekend_set(spec))
                 + '; bank holidays: ' + (', '.join(hol) if hol else 'none') + '.')
    lines.append('Tomorrow is ' + spoken_date(today + datetime.timedelta(days=1)) + '.')
    if prod_lines:
        lines.append('Products and LATEST promise dates:')
        lines.extend(prod_lines)
    lines.append('Day table (only dates marked OK can be recorded):')
    horizon = int(to_float(spec.get('date_table_days')) or 25)
    for j in range(horizon + 1):
        d = today + datetime.timedelta(days=j)
        tag = ' (today)' if j == 0 else (' (tomorrow)' if j == 1 else '')
        if not is_business_day(d, spec):
            nb = next_business_day_on_or_after(d, spec)
            s = 'NOT a business day (' + non_business_reason(d, spec) + '); next business day ' + spoken_date(nb)
        elif deadlines:
            ok = [lab for (_pid, lab, dl) in deadlines if dl is None or d <= dl]
            no = [lab for (_pid, lab, dl) in deadlines if dl is not None and d > dl]
            s = 'business day; ' + ('OK for: ' + ', '.join(ok) if ok else '')
            if no:
                s += ('; ' if ok else '') + 'NOT allowed, after the deadline for: ' + ', '.join(no)
        else:
            s = 'business day'
        lines.append('- ' + d.isoformat() + ' ' + WEEKDAY_NAMES[d.weekday()] + tag + ': ' + s)
    lines.append('Weekday words (said today):')
    for wd in range(7):
        t = resolve_weekday('this', wd, today, spec)
        n = resolve_weekday('next', wd, today, spec)
        lines.append('- "this ' + WEEKDAY_NAMES[wd] + '" = ' + spoken_date(t) + (' (already past)' if t < today else '')
                     + '; "next ' + WEEKDAY_NAMES[wd] + '" = ' + spoken_date(n))
    lw = last_business_day_of_week(today, spec, 0)
    ln = last_business_day_of_week(today, spec, 1)
    lines.append('Last business day of this week: ' + (spoken_date(lw) if lw else 'none')
                 + '. Last business day of next week: ' + (spoken_date(ln) if ln else 'none') + '.')
    lines.append('Persuasion attempt 1 date: ' + spoken_date(p1) + ' (' + v['attempt1_date'] + ').')
    cb = spec.get('callback') or dict()
    if cb:
        cdates = callback_allowed_dates(nowdt, spec)
        v['callback_dates'] = ', '.join(x.isoformat() for x in cdates)
        parts = []
        for x in cdates:
            start = cb.get('start', '00:00')
            if x == today and cb.get('must_be_after_now', True):
                parts.append(spoken_date(x) + ' after ' + nowdt.strftime('%H:%M') + ' until ' + cb.get('end', '23:59'))
            else:
                parts.append(spoken_date(x) + ' from ' + start + ' to ' + cb.get('end', '23:59'))
        lines.append('Callback allowed only: ' + '; '.join(parts) + ' (both ends included).')
    v['date_facts'] = '\n'.join(lines)
    return v
# ---- END PORTABLE ----


def portable_source():
    """Source text of the PORTABLE region (used by codegen)."""
    import os
    with open(os.path.abspath(__file__), 'r', encoding='utf-8') as f:
        src = f.read()
    a = src.index('# ---- BEGIN PORTABLE ----')
    b = src.index('# ---- END PORTABLE ----')
    return src[a:b]
