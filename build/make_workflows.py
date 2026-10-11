"""Generate out/brief-a.workflow.json and out/brief-b.workflow.json.

    python3 build/make_workflows.py
"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://freya-bank-mock.freyavoice.workers.dev/v1/"
HOLIDAYS = ["2026-10-26", "2026-11-11", "2026-11-26", "2026-12-25", "2027-01-01"]


def no_braces(code):
    assert "{{" not in code and "}}" not in code, code
    return code


# ---------------------------------------------------------------- tool builders

def api_tool(name, desc, fields, required, post=None, pre=None, mapping=None, retries=0):
    props = {"customer_id": {"type": "string", "default": "{{customer_id}}"}}
    props.update(fields)
    t = {
        "type": "function",
        "config": {"timeoutMs": 12000, "maxRetries": retries},
        "function": {
            "name": name,
            "handler": "__function__:api_call",
            "description": desc,
            "parameters": {"type": "object", "properties": {
                "url": {"type": "string", "default": BASE + name},
                "method": {"type": "string", "default": "POST"},
                "headers": {"type": "object", "properties": {"Content-Type": {"type": "string", "default": "application/json"}}},
                "body": {"type": "object", "properties": props, "required": required},
            }},
        },
    }
    if pre: t["pre_process_code"] = no_braces(pre)
    if post: t["post_process_code"] = no_braces(post)
    if mapping: t["response_mapping"] = mapping
    return t


# post-hook skeleton: normalise result, compute `what`, extra keys
POST_HEAD = """try:
    V = vars
except Exception:
    V = {}
try:
    if isinstance(result, dict):
        result.pop('header', None)
        d = result.get('data')
        if not isinstance(d, dict):
            d = {'ok': False, 'error': 'service_unavailable'}
            result['data'] = d
        if result.get('status') not in (None, 'success') or (result.get('status_code') or 200) >= 400:
            d['ok'] = False
"""
POST_TAIL = """except Exception:
    pass
"""


def indent(code, n=8):
    return "".join((" " * n + l if l.strip() else l) for l in code.splitlines(True))


VERIFY_PRE = r"""import re
try:
    b = config.get('body')
    if isinstance(b, dict):
        f = str(b.get('field') or '')
        a = str(b.get('answer') or '').strip()
        if f == 'phone_last4':
            dg = re.sub(r'[^0-9]', '', a)
            if len(dg) >= 4:
                b['answer'] = dg[-4:]
        elif f == 'date_of_birth' and not re.match(r'^\d{4}-\d{2}-\d{2}$', a):
            months = ['january','february','march','april','may','june','july','august','september','october','november','december']
            low = a.lower()
            mo = 0
            for i in range(12):
                if months[i] in low or re.search(r'\b' + months[i][:3] + r'\b', low):
                    mo = i + 1
                    break
            nums = re.findall(r'\d+', low)
            out = ''
            if mo and len(nums) >= 2:
                yr = [x for x in nums if len(x) == 4]
                dy = [x for x in nums if len(x) <= 2]
                if yr and dy:
                    out = '%s-%02d-%02d' % (yr[0], mo, int(dy[0]))
            elif len(nums) == 3:
                if len(nums[0]) == 4:
                    out = '%s-%02d-%02d' % (nums[0], int(nums[1]), int(nums[2]))
                elif len(nums[2]) == 4:
                    out = '%s-%02d-%02d' % (nums[2], int(nums[1]), int(nums[0]))
            if out:
                b['answer'] = out
except Exception:
    pass
"""

VERIFY_POST = POST_HEAD + indent("""left = d.get('wrong_answers_left')
try:
    left = int(left)
except Exception:
    left = None
if d.get('all_verified') is True:
    d['check_state'] = 'verified'
    d['what_to_do_next'] = 'Both security answers passed.'
elif d.get('hint') == 'day_month_swapped':
    d['check_state'] = 'pending'
    d['what_to_do_next'] = 'Day and month seem to be the wrong way round. Ask the customer to say the date of birth again with the month as a word, for example 14 March 1988. This is not counted as a wrong answer.'
elif d.get('verified') is False and left is not None and left <= 0:
    d['check_state'] = 'failed_out'
    d['what_to_do_next'] = 'Third wrong answer. The check has ended.'
elif d.get('verified') is True:
    d['check_state'] = 'pending'
    d['what_to_do_next'] = 'This answer is correct. Now ask the other security question: the last four digits of the phone number on file. Say nothing about the account.'
elif d.get('verified') is False:
    d['check_state'] = 'pending'
    d['what_to_do_next'] = 'That answer did not match. Politely ask the SAME question once more. Do not say what the right answer is and do not move to the other question.'
else:
    d['check_state'] = 'pending'
    d['what_to_do_next'] = 'The answer could not be checked (not counted as wrong). Ask the customer to repeat the same answer clearly, for a date: day, month as a word, and year.'
""") + POST_TAIL

GENERIC_POST = POST_HEAD + indent("""if d.get('ok') is True:
    d['what_to_do_next'] = OKMSG
else:
    d['what_to_do_next'] = FAILMSG
""") + POST_TAIL


def generic_post(okmsg, failmsg):
    return GENERIC_POST.replace("OKMSG", repr(okmsg)).replace("FAILMSG", repr(failmsg))


CREATE_PRE = """import json
try:
    b = config.get('body')
    f = json.loads(str(vars.get('facts_json') or '{}'))
    prods = f.get('products') or {}
    if isinstance(b, dict) and prods:
        pid = str(b.get('product_id') or '')
        if pid not in prods and len(prods) == 1:
            pid = list(prods.keys())[0]
            b['product_id'] = pid
        p = prods.get(pid)
        if p:
            try:
                amt = round(float(b.get('amount')), 2)
                if amt > p['past_due']:
                    amt = p['past_due']
                if amt < p['floor']:
                    amt = p['floor']
                b['amount'] = amt
            except Exception:
                pass
            dd = str(b.get('date') or '')[:10]
            nb = f.get('next_bd') or {}
            if dd < f.get('today', ''):
                dd = f.get('today', '')
            if dd in nb:
                dd = nb[dd]
            if dd > p['deadline']:
                dd = p['deadline']
            if dd:
                b['date'] = dd
except Exception:
    pass
"""

CREATE_POST_A = POST_HEAD + indent("""if d.get('ok') is True:
    d['promise_state'] = 'recorded'
    try:
        V['any_promise'] = 'yes'
    except Exception:
        pass
    d['what_to_do_next'] = 'The promise is recorded.'
else:
    n = 0
    try:
        n = int(V.get('cp_fail_n') or 0) + 1
        V['cp_fail_n'] = n
    except Exception:
        n = 0
    d['promise_state'] = 'failed'
    if n == 1:
        d['what_to_do_next'] = 'The promise was NOT recorded (first failure). Do not say it is recorded. Call create_promise once more right now with exactly the same product_id, amount and date.'
    elif n >= 2:
        d['what_to_do_next'] = 'The promise was NOT recorded (second failure). Tell the customer you could not record the promise because of a technical problem. Then thank them, say goodbye and call close_call with outcome no_promise and reason service_error.'
    else:
        d['what_to_do_next'] = 'The promise was NOT recorded. Do not say it is recorded. If this was the first failure, call create_promise once more with the same values. If it already failed before, tell the customer you could not record it, say goodbye and call close_call with outcome no_promise and reason service_error.'
""") + POST_TAIL

CREATE_POST_B = POST_HEAD + indent("""pid = ''
try:
    pid = str(V.get('create_promise_args.product_id') or (V.get('create_promise_args') or {}).get('product_id') or '')
except Exception:
    pid = ''
if d.get('ok') is True:
    try:
        V['any_promise'] = 'yes'
    except Exception:
        pass
    d['what_to_do_next'] = 'The promise for this product is recorded. If another confirmed product still has no create_promise call, call create_promise for it now. When every confirmed product is done, tell the customer which promises are recorded and say: You will receive a text message confirming this promise. Then continue with any product not handled yet, or close.'
else:
    d['what_to_do_next'] = 'The promise for this product was NOT recorded. Do not say it is recorded. If this is the first failure for this product, call create_promise once more right now with exactly the same values. If it already failed once for this product, keep the other promises, call add_note for this product with reason service_error, and tell the customer you could not record this one.'
""") + POST_TAIL

NOTE_POST = POST_HEAD + indent("""if d.get('ok') is True:
    d['what_to_do_next'] = 'The note is saved. Continue with the next product in order, or close the call if every product is handled.'
else:
    d['what_to_do_next'] = 'The note was not saved. Continue with the next product in order, or close the call if every product is handled.'
""") + POST_TAIL

TRANSFER_POST = POST_HEAD + indent("""if d.get('ok') is True:
    d['what_to_do_next'] = 'The transfer is done. Tell the customer a colleague will take over, thank them, say goodbye and call close_call with outcome transferred and the matching reason (restructuring queue: restructuring, general queue: human, support queue: support).'
else:
    d['what_to_do_next'] = 'The transfer FAILED. Do not say you are transferring them. Tell the customer you could not connect them right now.'
""") + POST_TAIL

CALLBACK_POST = generic_post(
    'The callback is booked. Tell the person when we will call back, thank them, say goodbye and call close_call with outcome not_reached and reason callback.',
    'The callback was NOT booked. Tell the person you could not book it. Thank them, say goodbye and call close_call with outcome not_reached and reason no_callback.')

CLOSE_POST = generic_post('The call is closed. Say nothing more.', 'The call is closed. Say nothing more.')

# close_call pre-hook: force the outcome that the recorded facts dictate.
CLOSE_PRE = """import json
try:
    b = config.get('body')
    if isinstance(b, dict):
        q = ''
        try:
            q = str(vars.get('transfer_to_agent_args.queue') or (vars.get('transfer_to_agent_args') or {}).get('queue') or '')
        except Exception:
            q = ''
        tok = str(vars.get('transfer_to_agent_response.data.ok') or '').lower() == 'true'
        if q and tok:
            b['outcome'] = 'transferred'
            b['reason'] = {'restructuring': 'restructuring', 'general': 'human', 'support': 'support'}.get(q, b.get('reason'))
        elif str(vars.get('any_promise') or '') == 'yes':
            b['outcome'] = 'promise'
        if b.get('outcome') in ('promise', 'paid') or not b.get('reason'):
            b.pop('reason', None)
except Exception:
    pass
"""


def verify_tool():
    return api_tool(
        "verify_identity",
        "Check ONE security answer. CALL it every time the customer gives an answer to a security question, before you say anything else.",
        {
            "field": {"type": "string", "enum": ["date_of_birth", "phone_last4"], "default": "{{field}}",
                      "description": "Which question was answered: date_of_birth or phone_last4."},
            "answer": {"type": "string", "default": "{{answer}}",
                       "description": "date_of_birth as YYYY-MM-DD (convert spoken dates; a date said only in numbers is day, month, year). phone_last4 as exactly four digits."},
        },
        ["field", "answer"], pre=VERIFY_PRE, post=VERIFY_POST,
        mapping=[{"path": "data.check_state", "variable": "id_state"}])


def callback_tool():
    return api_tool(
        "schedule_callback",
        "Book a callback for the customer. CALL it as soon as the person who answered gives a day and time inside the allowed callback window.",
        {
            "date": {"type": "string", "default": "{{date}}", "description": "Callback day as YYYY-MM-DD."},
            "time": {"type": "string", "default": "{{time}}", "description": "Callback time as HH:MM, 24 hour."},
        },
        ["date", "time"], post=CALLBACK_POST)


def transfer_tool(queues):
    return api_tool(
        "transfer_to_agent",
        "Hand the call to a human team. CALL it when a rule says to transfer: queue " + ", ".join(queues) + ".",
        {"queue": {"type": "string", "enum": queues, "default": "{{queue}}",
                   "description": "restructuring: new payment plan or lower instalments. general: the customer insists on a human. support: hardship case that accepted the support team."}},
        ["queue"], post=TRANSFER_POST)


def close_tool(outcomes, reasons_text):
    return api_tool(
        "close_call",
        "End the call record. CALL it exactly once, as the very last tool call, in the same message as your thank-you and goodbye.",
        {
            "outcome": {"type": "string", "enum": outcomes, "default": "{{outcome}}", "description": "How the call ended. One of: " + ", ".join(outcomes) + "."},
            "reason": {"type": "string", "default": "{{reason}}", "description": reasons_text},
        },
        ["outcome"], pre=CLOSE_PRE, post=CLOSE_POST)


def create_tool(single):
    fields = {
        "product_id": {"type": "string", "default": "{{product_id}}", "description": "product_id from the account facts, for example p1. Copy it exactly."},
        "amount": {"type": "number", "default": "{{amount}}", "description": "Amount the customer confirmed, as a number."},
        "date": {"type": "string", "default": "{{date}}", "description": "Payment date the customer confirmed, YYYY-MM-DD."},
    }
    return api_tool(
        "create_promise",
        "Record ONE payment promise for one product. CALL it only after the customer said a clear yes to your read-back. Never call it twice for a product that is already recorded.",
        fields, ["product_id", "amount", "date"], pre=CREATE_PRE,
        post=CREATE_POST_A if single else CREATE_POST_B,
        mapping=[{"path": "data.promise_state", "variable": "promise_state"}] if single else None)


def note_tool():
    return api_tool(
        "add_note",
        "Record why ONE product ends without a promise. CALL it once for each product that gets no promise (never on a call that is transferred).",
        {
            "product_id": {"type": "string", "default": "{{product_id}}", "description": "product_id from the account facts, for example p2."},
            "reason": {"type": "string", "enum": ["refused", "hardship", "dispute", "paid", "service_error"], "default": "{{reason}}",
                       "description": "One of: refused, hardship, dispute, paid, service_error."},
        },
        ["product_id", "reason"], post=NOTE_POST)


# ---------------------------------------------------------------- code

SETUP_CODE = r"""import datetime, json
try:
    dt = datetime
    HOL = ['2026-10-26', '2026-11-11', '2026-11-26', '2026-12-25', '2027-01-01']
    now_s = str(vars.get('now') or '').strip()
    try:
        now = dt.datetime.fromisoformat(now_s[:16])
    except Exception:
        try:
            now = dt.datetime.fromisoformat(now_s[:10] + 'T00:00')
        except Exception:
            now = dt.datetime.now()
    today = now.date()
    one = dt.timedelta(days=1)
    def isbd(d, HOL=HOL):
        return d.weekday() < 5 and d.isoformat() not in HOL
    def nextbd(d, isbd=isbd, one=one):
        while not isbd(d):
            d = d + one
        return d
    def nth_after(d, n, isbd=isbd, one=one):
        c = 0
        while c < n:
            d = d + one
            if isbd(d):
                c += 1
        return d
    def sp(d):
        return d.strftime('%A') + ' ' + str(d.day) + ' ' + d.strftime('%B') + ' ' + str(d.year)
    early = nth_after(today, 12)
    late = nth_after(today, 7)
    monday = today - dt.timedelta(days=today.weekday())
    def last_bd_of_week(mon, isbd=isbd, dt=dt):
        for k in range(4, -1, -1):
            x = mon + dt.timedelta(days=k)
            if isbd(x):
                return x
        return None
    lw = last_bd_of_week(monday)
    if lw is None or lw <= today:
        lw = last_bd_of_week(monday + dt.timedelta(days=7))
    nbd_after = nth_after(today, 1)
    nb = {}
    lines = []
    for k in range(0, 70):
        x = today + dt.timedelta(days=k)
        n = nextbd(x)
        nb[x.isoformat()] = n.isoformat()
        if k <= 45:
            if isbd(x):
                tag = 'business day'
            elif x.isoformat() in HOL:
                tag = 'BANK HOLIDAY, not allowed, next business day ' + n.isoformat()
            else:
                tag = 'weekend, not allowed, next business day ' + n.isoformat()
            lines.append(x.isoformat() + ' ' + x.strftime('%A') + ': ' + tag)
    names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    wk = []
    for i in range(7):
        a = monday + dt.timedelta(days=i)
        b2 = a + dt.timedelta(days=7)
        wk.append('this ' + names[i] + ' = ' + a.isoformat() + (' (past)' if a < today else '') + '; next ' + names[i] + ' = ' + b2.isoformat())
    cb = []
    if isbd(today) and now.hour < 19:
        cb.append('today ' + today.isoformat() + ' from ' + max(now + dt.timedelta(minutes=1), dt.datetime.combine(today, dt.time(10, 0))).strftime('%H:%M') + ' to 19:00')
    cb.append('next business day ' + nbd_after.isoformat() + ' (' + nbd_after.strftime('%A') + ') from 10:00 to 19:00')
    vars['today_iso'] = today.isoformat()
    vars['today_spoken'] = sp(today) + ', ' + now.strftime('%H:%M')
    vars['deadline_early'] = early.isoformat()
    vars['deadline_late'] = late.isoformat()
    vars['attempt1_date'] = lw.isoformat()
    vars['attempt1_spoken'] = sp(lw)
    vars['callback_window'] = ' or '.join(cb)
    vars['calendar_text'] = '\n'.join(lines)
    vars['weekday_text'] = '\n'.join(wk)
    vars['date_facts_json'] = json.dumps({'today': today.isoformat(), 'next_bd': nb, 'early': early.isoformat(), 'late': late.isoformat(), 'attempt1': lw.isoformat()})
    vars['setup_state'] = 'ok'
except Exception as e:
    vars['setup_state'] = 'error'
    vars['today_iso'] = str(vars.get('now') or '')[:10]
    vars['today_spoken'] = str(vars.get('now') or '')
    vars['deadline_early'] = ''
    vars['deadline_late'] = ''
    vars['attempt1_date'] = ''
    vars['attempt1_spoken'] = ''
    vars['callback_window'] = 'today or the next business day, 10:00 to 19:00, later than now'
    vars['calendar_text'] = ''
    vars['weekday_text'] = ''
    vars['date_facts_json'] = '{}'
"""

ACCOUNT_CODE = r"""import json, re, datetime
try:
    dt = datetime
    raw = vars.get('acct_products')
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = None
    prods = raw if isinstance(raw, list) else None
    if prods is None:
        for k in list(vars.keys()):
            v = vars.get(k)
            if str(k).endswith('products') and isinstance(v, list):
                prods = v
                break
            if str(k).endswith('products') and isinstance(v, str) and v.strip().startswith('['):
                try:
                    prods = json.loads(v)
                    break
                except Exception:
                    pass
    if prods is None:
        tmp = {}
        for k in list(vars.keys()):
            m = re.search(r'products\.(\d+)\.([A-Za-z_0-9]+)$', str(k))
            if m:
                tmp.setdefault(int(m.group(1)), {})[m.group(2)] = vars.get(k)
        if tmp:
            prods = [tmp[i] for i in sorted(tmp.keys())]
    df = json.loads(str(vars.get('date_facts_json') or '{}'))
    def num(x):
        try:
            return float(x)
        except Exception:
            return 0.0
    def money(x):
        x = round(float(x), 2)
        if abs(x - int(x)) < 0.001:
            return '{:,}'.format(int(x))
        return '{:,.2f}'.format(x)
    def sp(iso, dt=dt):
        d = dt.date.fromisoformat(iso)
        return d.strftime('%A') + ' ' + str(d.day) + ' ' + d.strftime('%B')
    facts = {}
    lines = []
    stmts = []
    order = []
    for i, p in enumerate(prods or []):
        if not isinstance(p, dict):
            continue
        pid = str(p.get('product_id') or ('p' + str(i + 1)))
        typ = str(p.get('type') or '')
        if typ == 'credit_card':
            words = 'credit card ending ' + str(p.get('card_last4') or '')
            floor = num(p.get('minimum_payment'))
            floor_name = 'minimum payment'
        elif typ == 'car_loan':
            words = 'car loan'
            floor = num(p.get('instalment_amount'))
            floor_name = 'instalment amount'
        else:
            words = 'personal loan'
            floor = num(p.get('instalment_amount'))
            floor_name = 'instalment amount'
        due = num(p.get('past_due'))
        late = int(num(p.get('days_late')))
        if late <= 7:
            band = 'early'
            dl = df.get('early', '')
            attempts = 1
        else:
            band = 'late'
            dl = df.get('late', '')
            attempts = 2
        a1 = df.get('attempt1', '')
        if a1 and dl and a1 > dl:
            a1 = dl
        facts[pid] = {'past_due': due, 'floor': floor, 'deadline': dl, 'words': words}
        order.append(pid)
        lines.append('- product_id ' + pid + ': ' + words + '. Full past-due amount ' + money(due) + ', ' + str(late) + ' days late. Floor (' + floor_name + ') ' + money(floor) + '. Band ' + band + '. DEADLINE ' + dl + ' (' + sp(dl) + '). Persuasion attempts allowed: ' + str(attempts) + '. Attempt 1 = ' + ('the full amount' ) + ' (or the floor if the customer said the full amount is too much) on ' + a1 + ' (' + sp(a1) + ').' + (' Attempt 2 = the floor ' + money(floor) + ' on the deadline ' + dl + ' (' + sp(dl) + ').' if attempts == 2 else ' ONLY ONE ATTEMPT: if attempt 1 is refused, make NO further offer on this product (not the floor, not another date); it ends without a promise, reason refused.'))
        stmts.append('your ' + words + ' has a past-due amount of ' + money(due) + ' and is ' + str(late) + ' days late')
    if facts:
        vars['acct_state'] = 'ok'
    else:
        vars['acct_state'] = 'error'
    vars['account_facts'] = '\n'.join(lines)
    vars['product_count'] = str(len(facts))
    vars['product_order'] = ', '.join(order)
    if len(stmts) == 1:
        vars['debt_statement'] = 'I am calling from the collections team about a late payment: ' + stmts[0] + '.'
    else:
        vars['debt_statement'] = 'I am calling from the collections team about late payments. ' + ' '.join(s[0].upper() + s[1:] + '.' for s in stmts)
    vars['today_question'] = 'Can you make this payment today?' if len(stmts) == 1 else 'Can you pay all of them today?'
    df['products'] = facts
    df['order'] = order
    vars['facts_json'] = json.dumps(df)
except Exception as e:
    vars['acct_state'] = 'error'
    vars['account_facts'] = ''
    vars['debt_statement'] = ''
    vars['product_count'] = '0'
    vars['product_order'] = ''
    vars['facts_json'] = '{}'
    vars['today_question'] = 'Can you make this payment today?'
"""

# ---------------------------------------------------------------- nodes


def cond_eq(var, *vals):
    return {"logic": "or", "conditions": [{"variable": var, "operator": "equals", "operand": v} for v in vals]}


def cond_gt(var, n):
    return {"logic": "or", "conditions": [{"variable": var, "operator": "greater_than", "operand": n}]}


ALWAYS = {"operator": "always"}
TO_HANGUP = {"target_node": "hangup", "description": "close_call was called", "condition": cond_gt("close_call_success_count", 0)}


def code_node(name, code, nxt, transitions=None):
    return {
        "name": name, "node_type": "code", "passthrough": True, "passthrough_default_transition": nxt,
        "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True,
        "pre_actions": [{"type": "function", "function": {"name": "code_exec", "handler": "__function__:code_exec",
                         "parameters": {"type": "object", "properties": {
                             "code": {"type": "string", "default": no_braces(code)},
                             "timeout_ms": {"type": "number", "default": 10000}}}}}],
        "transitions": (transitions or []) + [{"target_node": nxt, "description": "always", "condition": ALWAYS}],
    }


def engine_call_node(name, fname, body_props, nxt, on_enter, mapping=None, transitions=None, retries=2):
    props = {"customer_id": {"type": "string", "default": "{{customer_id}}"}}
    props.update(body_props)
    n = {
        "name": name, "node_type": "api_request", "passthrough": True, "passthrough_default_transition": nxt,
        "on_enter": on_enter, "disable_inactivity_monitor": True,
        "pre_actions": [{"type": "function", "config": {"timeoutMs": 12000, "maxRetries": retries}, "function": {
            "name": fname, "handler": "__function__:api_call", "description": fname,
            "parameters": {"type": "object", "properties": {
                "url": {"type": "string", "default": BASE + fname},
                "method": {"type": "string", "default": "POST"},
                "headers": {"type": "object", "properties": {"Content-Type": {"type": "string", "default": "application/json"}}},
                "body": {"type": "object", "properties": props, "required": []}}}}}],
        "transitions": (transitions or []) + [{"target_node": nxt, "description": "always", "condition": ALWAYS}],
    }
    if mapping: n["response_mapping"] = mapping
    return n


def conv(name, task, tools, transitions, on_enter=None, first_only=True):
    n = {"name": name, "node_type": "conversation", "task_message": task, "tools": tools,
         "transitions": transitions, "max_node_turns": 60}
    if on_enter:
        n["on_enter"] = on_enter
        n["on_enter_first_entry_only"] = first_only
    return n


HANGUP = {"name": "hangup", "node_type": "end_call", "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True,
          "transitions": [], "terminal": {"type": "function", "function": {"name": "call_closed", "handler": "__function__:end_call",
          "parameters": {"type": "object", "properties": {"message_mode": {"type": "string", "default": "none"}}}}}}


SYSTEM = """You are the digital assistant of Freya Bank, making an outbound phone call to {{title}} {{first_name}} {{last_name}}. Speak English. Keep every turn to one or two short sentences. Address the customer as {{title}} {{last_name}}.
Current date and time: {{now}} ({{today_spoken}}). Every date rule uses this date, never any other clock.

Rules for every step:
- When a rule says to use a tool, CALL the tool. Saying you did it is not enough. One tool call per message. After every tool result, speak to the customer or call the next tool. Never end a turn with nothing.
- Every tool result has a what_to_do_next field. Follow it.
- If a tool call fails, say so. Never say something is recorded, booked or transferred unless the tool returned ok true.
- Never invent figures, dates or reasons. If asked something your facts do not cover, say you do not have that information.
- If asked whether you are a robot or an AI: say you are Freya Bank's digital assistant, then continue.
- If asked whether this call is a scam: say they can verify this call by phoning Freya Bank's customer service number, then continue.
- Never offer a discount, a waiver, an instalment plan or any term not given to you.
- To end the call: in ONE message thank the customer, say goodbye, and call close_call with the outcome and reason. close_call is always the very last tool call and is called only once."""


IDENTITY_TASK = """You already said: "Hello, I am a digital assistant calling from Freya Bank. This call is recorded. Am I speaking with {{title}} {{last_name}}?"
Your job in this step: make sure the right person is on the line, then pass the two security questions. Until both pass, never say why you are calling and never mention collections, a debt, a payment, an amount or a product, to anyone. If asked what the call is about, say you can only discuss it with {{title}} {{last_name}} after a short security check.

A. WHO IS ON THE LINE
- Only "yes", "that's me", "speaking" or the customer saying their own name confirms it. "Hello", "go ahead", "who is this" do NOT confirm.
- If not confirmed: first answer any question they asked (for "who is this": you are Freya Bank's digital assistant), then ask once more "Am I speaking with {{title}} {{last_name}}?". If it is still unclear after this second ask: thank them, say goodbye and call close_call with outcome not_reached, reason unclear.
- If someone else answered (a relative, a colleague, anyone not the customer): say nothing about the reason for the call, and ask when {{title}} {{last_name}} can be reached. They may not answer security questions and may not hear anything about the account, even if they offer to pay.
  - Allowed callback times: {{callback_window}}. Anything else (another day, earlier than 10:00, later than 19:00, already past) is outside the window.
  - Inside the window: call schedule_callback with date YYYY-MM-DD and time HH:MM (for "around eleven" use 11:00). Then thank them, say goodbye, close_call not_reached / callback.
  - Outside the window: ask once for another time inside the window, naming the window. If the second answer is also outside it, or they cannot say: do not schedule; thank them, goodbye, close_call not_reached / no_callback.
- "This number does not belong to that person" / wrong number: apologise, goodbye, close_call not_reached / wrong_number.
- The customer has died: say exactly "I am sorry for your loss." Ask nothing else, say goodbye, close_call not_reached / deceased.

B. SECURITY QUESTIONS (only after the customer confirmed who they are)
- Say you need to ask two short security questions. Ask ONE at a time: first the date of birth, then the last four digits of the phone number on file.
- After each answer call verify_identity at once (field date_of_birth with answer YYYY-MM-DD, field phone_last4 with four digits). A date said only in numbers is day, then month, then year. Then follow what_to_do_next.
- If the customer gives only part of an answer, ask for the rest before calling the tool.
- Refusing to answer, or asking what the call is about instead of answering: the first time, explain once that these questions protect their account and ask again. The second time: thank them, goodbye, close_call not_verified / declined.
- If the customer says they do not want to talk: the first time, say it only takes a moment and ask again. The second time: close_call not_verified / declined.
- If they ask for a human: ask once whether you can help them first. If they insist, call transfer_to_agent with queue general; after it succeeds close_call transferred / human.

Never call get_account or talk about money in this step."""

ID_FAIL_LINE = "I am sorry, I could not verify your identity. Please use the Freya Bank mobile app or visit a branch. Thank you for your time, {{title}} {{last_name}}. Goodbye."


def common_nodes(negotiate_target, close_outcomes_id):
    nodes = {}
    nodes["setup"] = code_node("setup", SETUP_CODE, "identity")
    nodes["identity"] = conv(
        "identity", IDENTITY_TASK,
        [verify_tool(), callback_tool(), transfer_tool(["general"]),
         close_tool(["not_reached", "not_verified", "transferred"],
                    "not_reached: callback, no_callback, wrong_number, deceased or unclear. not_verified: declined. transferred: human.")],
        [TO_HANGUP,
         {"target_node": "fetch_account", "description": "Both security answers passed",
          "condition": {"logic": "or", "conditions": [
              {"variable": "id_state", "operator": "equals", "operand": "verified"},
              {"variable": "verify_identity_response.data.all_verified", "operator": "equals", "operand": "true"},
              {"variable": "verify_identity_response.data.all_verified", "operator": "equals", "operand": "True"}]}},
         {"target_node": "identity_failed", "description": "Three wrong answers", "condition": cond_eq("id_state", "failed_out")}],
        on_enter={"type": "tts", "text": "Hello, I am a digital assistant calling from Freya Bank. This call is recorded. Am I speaking with {{title}} {{last_name}}?"})
    nodes["identity_failed"] = engine_call_node(
        "identity_failed", "close_call",
        {"outcome": {"type": "string", "default": "not_verified"}, "reason": {"type": "string", "default": "failed"}},
        "hangup", {"type": "tts", "text": ID_FAIL_LINE}, retries=1)
    nodes["fetch_account"] = engine_call_node(
        "fetch_account", "get_account", {}, "account_facts", {"type": "silent"},
        mapping=[{"path": "data.products", "variable": "acct_products"}])
    nodes["account_facts"] = code_node(
        "account_facts", ACCOUNT_CODE, negotiate_target,
        [{"target_node": "account_error", "description": "No account data", "condition": cond_eq("acct_state", "error")}])
    nodes["account_error"] = engine_call_node(
        "account_error", "close_call",
        {"outcome": {"type": "string", "default": "no_promise"}, "reason": {"type": "string", "default": "service_error"}},
        "hangup", {"type": "tts", "text": "Thank you, you are verified. I am sorry, I cannot reach your account details right now because of a technical problem, so I cannot go further today. Thank you for your time, {{title}} {{last_name}}. Goodbye."}, retries=1)
    nodes["hangup"] = HANGUP
    return nodes


DATE_RULES = """DATES (today is {{today_iso}})
Calendar (only business days are allowed as a promise date):
{{calendar_text}}
Weekday words:
{{weekday_text}}
- A promise date must be today or later, a business day, and not after the product's DEADLINE.
- Weekend day or bank holiday on or before the deadline: say it is not a business day and offer the next business day from the calendar.
- A date after the deadline: say the latest date you can record is the deadline (say the date) and offer it. If the customer refuses the deadline, that is a flat refusal.
- Vague period ("next week", "end of the month", "when my salary comes", "the week after next"): ask ONCE for the exact day. If they still give no exact day, propose the deadline.
- "next <weekday>" = that weekday in the following calendar week; "this <weekday>" = the one in the current week (use the weekday words above). "tomorrow" = the day after today.
- When you say a date, say weekday, day and month, for example "Friday 16 October"."""

AMOUNT_RULES = """AMOUNTS
- Ask for the full past-due amount first. NEVER ask how much they can pay; you propose every amount. If they say "you tell me", propose the amount yourself.
- If the customer says the full amount is too much: offer the floor, once, and say that the rest stays overdue.
- A customer-proposed amount from the floor up to the full amount (both included): accept it. Below the floor: say it cannot be recorded and offer the floor once; if they do not accept it, that is a flat refusal."""

SPECIAL_RULES = """OTHER SITUATIONS (they come before persuasion)
- Illness, a death in the family or job loss: say ONE short sentence of sympathy, make NO persuasion attempt, and offer to connect them with the customer support team. Accepts: call transfer_to_agent with queue support. Declines: OUTCOME_HARDSHIP. If they still name a date or amount themselves, handle it as a normal promise.
- "I already paid": say that payments can take one business day to appear. Take no promise. OUTCOME_PAID
- "This debt is not mine", "I never had this product", or the product was closed or paid off in the past: do not argue, take no promise. OUTCOME_DISPUTE
- A new payment plan or lower instalments: do not describe any plan. Call transfer_to_agent with queue restructuring. OUTCOME_RESTRUCT
- Wants a human: ask once whether you can help first. If they insist, call transfer_to_agent with queue general.
- Says twice that they do not want to talk: OUTCOME_REFUSED
- After a transfer_to_agent succeeds: thank them, goodbye, close_call with outcome transferred and reason restructuring / human / support."""


def brief_a():
    nodes = common_nodes("negotiate", None)
    special = (SPECIAL_RULES
               .replace("OUTCOME_HARDSHIP", "thank them, goodbye, close_call no_promise / hardship.")
               .replace("OUTCOME_PAID", "Thank them, goodbye, close_call with outcome paid.")
               .replace("OUTCOME_DISPUTE", "Thank them, goodbye, close_call no_promise / dispute.")
               .replace("OUTCOME_RESTRUCT", "")
               .replace("OUTCOME_REFUSED", "thank them, goodbye, close_call no_promise / refused."))
    task = """The customer is verified. You already told them the debt and asked "Can you make this payment today?".

ACCOUNT FACTS
{{account_facts}}

""" + DATE_RULES + "\n\n" + AMOUNT_RULES + "\n\n" + special + """

GETTING THE PROMISE
- Yes to today: the full amount today.
- A date or an amount the customer proposes is NEVER a refusal: check it with the DATES and AMOUNTS rules and propose the valid version.
- A flat refusal or a non-answer (including a no to paying today with no date and no amount) uses one persuasion attempt:
  - Attempt 1: propose the full amount (or the floor if they already said the full amount is too much) on the Attempt 1 date in the facts.
  - Attempt 2, only if the facts allow 2 attempts: propose the floor on the deadline.
  - When the allowed attempts are used up, stop. Never repeat an offer they already refused. Thank them, goodbye, close_call no_promise / refused.
  - Offering the floor is allowed only (a) once after the customer says the full amount is too much, or (b) as attempt 2 when the facts allow 2 attempts. With ONLY ONE ATTEMPT and a flat refusal, make no floor offer.
- Count your attempts carefully. Offering the floor after "too much" is not a persuasion attempt.

CONFIRMING
- When an amount and a date are agreed, read back the product, the amount and the date, and ask "Do you confirm?".
- Only after a clear yes, call create_promise with the product_id, the amount and the date (YYYY-MM-DD). If they change the date or amount, check it again and read back again.
- Never say the promise is recorded before create_promise returns ok true. Follow what_to_do_next after the result."""
    nodes["negotiate"] = conv(
        "negotiate", task,
        [create_tool(True), transfer_tool(["restructuring", "general", "support"]),
         close_tool(["promise", "paid", "transferred", "no_promise"],
                    "Leave empty for promise and paid. transferred: restructuring, human or support. no_promise: refused, hardship, dispute or service_error.")],
        [TO_HANGUP,
         {"target_node": "promise_done", "description": "The promise was recorded", "condition": cond_eq("promise_state", "recorded")}],
        on_enter={"type": "tts", "text": "Thank you, {{title}} {{last_name}}. {{debt_statement}} {{today_question}}"})
    nodes["promise_done"] = conv(
        "promise_done",
        """The promise is recorded and you have just said that the customer will receive a text message confirming it.
- A recorded promise cannot be changed or cancelled in this call. If the customer asks, say they can change it in the Freya Bank mobile app.
- If they ask for a new payment plan or lower instalments: call transfer_to_agent with queue restructuring. If they insist on a human after you asked once whether you can help: queue general. After a successful transfer: goodbye and close_call transferred with reason restructuring or human.
- Otherwise: thank them, say goodbye and call close_call with outcome promise.""",
        [transfer_tool(["restructuring", "general", "support"]),
         close_tool(["promise", "transferred"], "Leave empty for promise. transferred: restructuring, human or support.")],
        [TO_HANGUP],
        on_enter={"type": "tts", "text": "Thank you, your promise is recorded. You will receive a text message confirming this promise. Is there anything else I can help you with?"})
    return {"initial_node": "setup", "system_prompt": SYSTEM, "nodes": nodes, "global_nodes": {},
            "test_variables": {"customer_id": "c_test", "first_name": "Daniel", "last_name": "Reyes", "title": "Mr", "now": "2026-10-14T11:00"}}


def brief_b():
    nodes = common_nodes("negotiate", None)
    special = (SPECIAL_RULES
               .replace("OUTCOME_HARDSHIP", "make no promise on the products affected (note them hardship) and go on.")
               .replace("OUTCOME_PAID", "If it is about one product, note that product paid and continue with the others.")
               .replace("OUTCOME_DISPUTE", "Note that product dispute and continue with the others.")
               .replace("OUTCOME_RESTRUCT", "Promises already recorded stay. Promises agreed but not yet recorded are NOT recorded. Add no notes at all.")
               .replace("OUTCOME_REFUSED", "note every remaining product refused, then close."))
    task = """The customer is verified. You already stated every late product and asked whether they can pay all of them today.

ACCOUNT FACTS (in get_account order; every product has its own band, deadline, floor and attempts)
{{account_facts}}

""" + DATE_RULES + "\n\n" + AMOUNT_RULES + "\n\n" + special + """

GETTING THE PROMISES
- Yes to all today: the full amount of every product, today.
- If not: go through the products one by one in the order above. Do not ask about today again for each product. Each product starts at its own attempt 1.
- A date or an amount the customer proposes is NEVER a refusal: check it against THAT product's rules.
- One date named for everything: use it for each product whose deadline allows it; a product whose deadline is earlier is recorded on its own deadline, and you say so in the read-back.
- A flat refusal or non-answer on a product uses one of THAT product's attempts:
  - Attempt 1: the full amount (or the floor if they said the full amount is too much) on that product's Attempt 1 date.
  - Attempt 2, only for products that allow 2 attempts: the floor on that product's deadline.
  - When a product's attempts are used up, stop for that product (no promise, reason refused) and go to the next product. Never repeat a refused offer.
  - Offering the floor is allowed only (a) once after the customer says the full amount is too much, or (b) as attempt 2 of a product that allows 2 attempts. An early-band product with a flat refusal gets attempt 1 only and NO floor offer.
- While going through the products, do NOT read back or ask "Do you confirm?" per product. Just note what was agreed and move to the next product.

CONFIRMING AND RECORDING
- When every product is handled, read back ALL agreed promises together (product, amount, date for each) and ask ONE "Do you confirm?".
- After a clear yes, call create_promise once per agreed product, one call per message, in order, each with that product's product_id, amount and date (YYYY-MM-DD).
- If a create_promise fails, follow what_to_do_next (retry once; after a second failure keep the others and note it service_error).
- After the promises are recorded, say: "You will receive a text message confirming this promise."
- Then call add_note once for each product WITHOUT a recorded promise, with its reason: refused, hardship, dispute, paid or service_error. This applies even when no product gets a promise. Never add notes on a transferred call.
- A recorded promise cannot be changed or cancelled in this call; if asked, say they can change it in the mobile app.

CLOSING (after all promises and notes)
- At least one promise recorded: close_call outcome promise.
- No promise and every product noted paid: close_call outcome paid.
- No promise otherwise: close_call outcome no_promise with the reason of the FIRST product (in the order above) whose note is not paid.
- After a transfer: close_call transferred with reason restructuring, human or support."""
    nodes["negotiate"] = conv(
        "negotiate", task,
        [create_tool(False), note_tool(), transfer_tool(["restructuring", "general", "support"]),
         close_tool(["promise", "paid", "transferred", "no_promise"],
                    "Leave empty for promise and paid. transferred: restructuring, human or support. no_promise: refused, hardship, dispute or service_error.")],
        [TO_HANGUP],
        on_enter={"type": "tts", "text": "Thank you, {{title}} {{last_name}}. {{debt_statement}} {{today_question}}"})
    return {"initial_node": "setup", "system_prompt": SYSTEM, "nodes": nodes, "global_nodes": {},
            "test_variables": {"customer_id": "c_test", "first_name": "Daniel", "last_name": "Reyes", "title": "Mr", "now": "2026-10-14T11:00"}}


if __name__ == "__main__":
    out = ROOT / "out"; out.mkdir(exist_ok=True)
    (out / "brief-a.workflow.json").write_text(json.dumps(brief_a(), indent=1))
    (out / "brief-b.workflow.json").write_text(json.dumps(brief_b(), indent=1))
    print("written")
