"""Emit Python source strings for Freya code_exec nodes and api_call pre/post hooks.

Rules honoured by every emitted string (see docs/tools-and-code.md):
  * only json / re / datetime,
  * reads inputs from `vars` defensively, writes STRINGS into `vars`,
  * never raises (outer try/except with fallbacks),
  * contains no double curly braces (spec is baked as a JSON text whose braces are
    written as \\x7b / \\x7d escapes inside a Python string literal).
All helpers live inside one wrapper function so they work whatever globals/locals
split the sandbox uses for exec().
"""
import json
import textwrap

try:
    from . import calendar_rules
except ImportError:  # run as a plain script
    import calendar_rules  # type: ignore


def spec_literal(obj):
    """Python expression text that evaluates to json.loads(<obj as JSON>) without any curly braces."""
    lit = repr(json.dumps(obj, ensure_ascii=True))
    return 'json.loads(' + lit.replace('{', '\\x7b').replace('}', '\\x7d') + ')'


def _str_lit(s):
    return repr(str(s)).replace('{', '\\x7b').replace('}', '\\x7d')


def _assert_safe(code):
    if '{{' in code or '}}' in code:
        raise ValueError('generated code contains double curly braces')
    compile(code, '<freya-snippet>', 'exec')
    return code


def _wrap(fn_name, args, body, outer_call, fallback):
    portable = textwrap.indent(calendar_rules.portable_source(), '    ')
    code = ('def ' + fn_name + '(' + args + '):\n'
            '    import json\n    import re\n    import datetime\n'
            + portable + '\n'
            + textwrap.indent(body, '    ') + '\n'
            'try:\n'
            + textwrap.indent(outer_call, '    ') + '\n'
            'except Exception:\n'
            + textwrap.indent(fallback + '\npass', '    ') + '\n')
    return _assert_safe(code)


def emit_date_facts_code(spec):
    """Code node snippet: writes date_facts, today, attempt1_date, callback_dates and per product
    p<i>_id/label/past_due/days_late/band/deadline/deadline_spoken/floor/attempts/attempt1_date
    (+ unprefixed copies for product 1) into vars. Run once at start and again after get_account."""
    body = 'SPEC = ' + spec_literal(spec) + '\ncompute_all(v, SPEC)\n'
    fallback = ("try:\n"
                "    if not vars.get('date_facts'):\n"
                "        vars['date_facts'] = 'Today: ' + str(vars.get('now') or '') + '. Date facts unavailable.'\n"
                "    for _k in ('today', 'deadline', 'floor', 'band', 'attempts', 'product_facts', 'attempt1_date'):\n"
                "        if vars.get(_k) is None:\n"
                "            vars[_k] = ''\n"
                "except Exception:\n"
                "    pass")
    return _wrap('_freya_date_facts', 'v', body, '_freya_date_facts(vars)', fallback)


def emit_get_account_post_hook(spec):
    """post_process_code for get_account: annotates each product in result['data'] with band,
    latest_promise_date, floor_amount, persuasion_attempts, label; also fills vars when available."""
    body = ('SPEC = ' + spec_literal(spec) + '\n'
            "result.pop('header', None)\n"
            "d = result.get('data')\n"
            "d = _maybe_json(d)\n"
            "if not isinstance(d, dict):\n"
            "    return\n"
            "result['data'] = d\n"
            "prods = _maybe_json(d.get('products'))\n"
            "if not isinstance(prods, list):\n"
            "    prods = []\n"
            "nowv = v.get('now') if isinstance(v, dict) else None\n"
            "today = to_date(nowv)\n"
            "for i, p in enumerate(prods):\n"
            "    if not isinstance(p, dict):\n"
            "        continue\n"
            "    band = band_for(p.get('days_late'), SPEC, p.get('type')) or dict()\n"
            "    p['label'] = product_label(p, SPEC)\n"
            "    p['band'] = str(band.get('name') or '')\n"
            "    p['persuasion_attempts'] = int(to_float(band.get('attempts')) or 0)\n"
            "    fl = floor_for(p, SPEC)\n"
            "    p['floor_amount'] = fl\n"
            "    if today is not None:\n"
            "        dl = deadline_from_band(band, today, SPEC)\n"
            "        p['latest_promise_date'] = dl.isoformat() if dl else ''\n"
            "        p['latest_promise_date_spoken'] = spoken_date(dl) if dl else ''\n"
            "if isinstance(v, dict):\n"
            "    try:\n"
            "        v['products'] = json.dumps(prods)\n"
            "        compute_all(v, SPEC)\n"
            "    except Exception:\n"
            "        pass\n"
            "d['what_to_do_next'] = 'State every late product in words with its past-due amount and days late. Use only the band, floor and latest_promise_date given here.'\n")
    outer = ("try:\n"
             "    _v = vars if isinstance(vars, dict) else None\n"
             "except Exception:\n"
             "    _v = None\n"
             "_freya_post_account(result, _v)")
    return _wrap('_freya_post_account', 'result, v', body, outer, '')


def emit_verify_identity_pre_hook(spec):
    """pre_process_code for verify_identity: normalise date answers to YYYY-MM-DD (digits read in
    spec['identity']['numeric_date_order'], default DMY) and digits-only answers to digits."""
    ident = spec.get('identity') or dict()
    order = ident.get('numeric_date_order', 'DMY')
    date_fields = [q.get('field') for q in ident.get('questions') or [] if q.get('type') == 'date']
    digit_fields = [q.get('field') for q in ident.get('questions') or [] if q.get('type') == 'digits']
    answer_param = ident.get('answer_param', 'answer')
    field_param = ident.get('field_param', 'field')
    body = ('DATE_FIELDS = ' + spec_literal(date_fields) + '\n'
            'DIGIT_FIELDS = ' + spec_literal(digit_fields) + '\n'
            'AP = ' + _str_lit(answer_param) + '\n'
            'FP = ' + _str_lit(field_param) + '\n'
            'body = config.get(\'body\') if isinstance(config, dict) else None\n'
            'if isinstance(body, str):\n'
            '    body = _maybe_json(body)\n'
            'src = body if isinstance(body, dict) else v\n'
            'field = str(src.get(FP) or v.get(FP) or \'\')\n'
            'ans = src.get(AP) if src.get(AP) is not None else v.get(AP)\n'
            'new = ans\n'
            'if field in DATE_FIELDS or (not field and re.search(r\'[a-zA-Z/.]\', str(ans or \'\')) and len(re.findall(r\'\\d+\', str(ans or \'\'))) >= 2):\n'
            '    new = normalize_date_answer(ans, ' + _str_lit(order) + ')\n'
            'elif field in DIGIT_FIELDS:\n'
            '    new = re.sub(r\'\\D\', \'\', str(ans or \'\')) or ans\n'
            'if new != ans:\n'
            '    if isinstance(body, dict):\n'
            '        body[AP] = new\n'
            '        config[\'body\'] = body\n'
            '    if isinstance(v, dict):\n'
            '        v[AP] = new\n')
    outer = ("try:\n"
             "    _v = vars if isinstance(vars, dict) else dict()\n"
             "except Exception:\n"
             "    _v = dict()\n"
             "try:\n"
             "    _c = config\n"
             "except Exception:\n"
             "    _c = dict()\n"
             "_freya_pre_verify(_c, _v)")
    return _wrap('_freya_pre_verify', 'config, v', body, outer, '')


def _simple_hook(body):
    code = ('try:\n'
            "    if isinstance(result, dict):\n"
            "        result.pop('header', None)\n"
            + textwrap.indent(body, '        ') + '\n'
            'except Exception:\n'
            '    pass\n')
    return _assert_safe(code)


def emit_verify_identity_post_hook(spec):
    """post_process_code for verify_identity: what_to_do_next for verified / wrong / swapped / unreadable / locked."""
    ident = spec.get('identity') or dict()
    fail_say = ident.get('fail_instruction', 'Do NOT state the debt. Close the call as the brief says for failed identity.')
    swap_say = ident.get('swap_instruction', 'Day and month look swapped. Ask the customer to say the month as a word. This retry is NOT a wrong answer.')
    body = ("d = result.get('data')\n"
            "if isinstance(d, str):\n"
            "    try:\n"
            "        import json\n"
            "        d = json.loads(d)\n"
            "        result['data'] = d\n"
            "    except Exception:\n"
            "        d = None\n"
            "if not isinstance(d, dict):\n"
            "    d = dict(raw=str(d))\n"
            "    result['data'] = d\n"
            "def _b(x):\n"
            "    return str(x).strip().lower() in ('true', '1', 'yes')\n"
            "left = None\n"
            "for _k in ('wrong_answers_left', 'attempts_left', 'tries_left', 'remaining_attempts'):\n"
            "    if d.get(_k) is not None:\n"
            "        left = d.get(_k)\n"
            "        break\n"
            "try:\n"
            "    left = int(left) if left is not None else None\n"
            "except Exception:\n"
            "    left = None\n"
            "verified = _b(d.get('verified', d.get('correct', d.get('match'))))\n"
            "allv = _b(d.get('all_verified', d.get('fully_verified', d.get('identity_verified'))))\n"
            "hint = str(d.get('hint') or '')\n"
            "ok = d.get('ok')\n"
            "if allv:\n"
            "    msg = 'IDENTITY VERIFIED. All security questions passed. Go on to the next step now.'\n"
            "elif verified:\n"
            "    msg = 'Correct. Ask the NEXT security question now (one question only).'\n"
            "elif 'swap' in hint:\n"
            "    msg = " + _str_lit(swap_say) + "\n"
            "elif ok is not None and not _b(ok) and left is None:\n"
            "    msg = 'The answer could not be read. It does NOT count as a wrong answer. Ask the same question again.'\n"
            "elif left is not None and left <= 0:\n"
            "    msg = 'No wrong answers left. Identity check FAILED. ' + " + _str_lit(fail_say) + "\n"
            "elif left is not None:\n"
            "    msg = 'Wrong answer. ' + str(left) + ' wrong answer(s) left in total. Ask the same question again. Do not give any account details.'\n"
            "else:\n"
            "    msg = 'Not verified. Ask the same question again. Do not give any account details.'\n"
            "d['what_to_do_next'] = msg\n")
    return _simple_hook(body)


def emit_create_promise_post_hook(spec):
    """post_process_code for create_promise: ok -> say recorded (+ SMS sentence); failure -> retry policy."""
    sms = spec.get('sms_sentence') or ''
    retries = int(spec.get('promise_retry_limit', 1) or 0)
    fail_close = spec.get('promise_fail_instruction',
                          'Say you could not record the promise and close the call as the brief says for a service error.')
    ok_msg = 'The promise IS recorded. Tell the customer it is recorded.'
    if sms:
        ok_msg += ' Then say exactly: "' + sms + '"'
    body = ("d = result.get('data')\n"
            "if isinstance(d, str):\n"
            "    try:\n"
            "        import json\n"
            "        d = json.loads(d)\n"
            "        result['data'] = d\n"
            "    except Exception:\n"
            "        d = None\n"
            "if not isinstance(d, dict):\n"
            "    d = dict(raw=str(d))\n"
            "    result['data'] = d\n"
            "ok = str(d.get('ok')).strip().lower() in ('true', '1') or bool(d.get('promise_id'))\n"
            "try:\n"
            "    sc = int(result.get('status_code') or 200)\n"
            "except Exception:\n"
            "    sc = 200\n"
            "if sc >= 400 or str(result.get('status') or '').lower() in ('error', 'failed', 'failure'):\n"
            "    ok = False\n"
            "fails = 0\n"
            "try:\n"
            "    if isinstance(vars, dict):\n"
            "        fails = int(vars.get('create_promise_fail_count') or 0)\n"
            "except Exception:\n"
            "    fails = 0\n"
            "if ok:\n"
            "    d['what_to_do_next'] = " + _str_lit(ok_msg) + "\n"
            "    try:\n"
            "        if isinstance(vars, dict):\n"
            "            vars['promise_recorded'] = 'yes'\n"
            "    except Exception:\n"
            "        pass\n"
            "else:\n"
            "    fails += 1\n"
            "    try:\n"
            "        if isinstance(vars, dict):\n"
            "            vars['create_promise_fail_count'] = str(fails)\n"
            "    except Exception:\n"
            "        pass\n"
            "    if fails <= " + str(retries) + ":\n"
            "        d['what_to_do_next'] = 'NOT recorded. Do NOT say it is recorded. Call create_promise again now, once, with the same values.'\n"
            "    else:\n"
            "        d['what_to_do_next'] = 'NOT recorded again. Do NOT say it is recorded. ' + " + _str_lit(fail_close) + "\n")
    return _simple_hook(body)


def emit_generic_post_hook(ok_text='Done. Continue.', fail_text='The action failed. Nothing was recorded. You may call it once more.'):
    """post_process_code for other api_call tools: drop headers, add what_to_do_next by ok flag."""
    body = ("d = result.get('data')\n"
            "if isinstance(d, dict):\n"
            "    ok = str(d.get('ok')).strip().lower() in ('true', '1')\n"
            "    d['what_to_do_next'] = " + _str_lit(ok_text) + " if ok else " + _str_lit(fail_text) + "\n")
    return _simple_hook(body)
