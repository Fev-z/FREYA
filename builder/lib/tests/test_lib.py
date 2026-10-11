"""Run: python -m pytest builder/lib/tests  or  python builder/lib/tests/test_lib.py"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from lib import calendar_rules as cr  # noqa: E402
from lib import codegen  # noqa: E402

D = datetime.date
NOW = '2026-10-14T11:00'

# Brief A spec, written BY HAND from briefs/brief-a.md (test fixture only).
SPEC_A = {
    'weekend_days': ['Saturday', 'Sunday'],
    'holidays': ['2026-10-26', '2026-11-11', '2026-11-26', '2026-12-25', '2027-01-01'],
    'week_start_day': 'Monday',
    'bands': [
        {'name': 'early', 'min_days_late': 1, 'max_days_late': 7,
         'deadline_unit': 'business_days', 'deadline_count': 12, 'attempts': 1},
        {'name': 'late', 'min_days_late': 8, 'max_days_late': 45,
         'deadline_unit': 'business_days', 'deadline_count': 7, 'attempts': 2},
    ],
    'floor_field_by_product_type': {'credit_card': 'minimum_payment',
                                    'personal_loan': 'instalment_amount', 'car_loan': 'instalment_amount'},
    'product_labels': {'credit_card': 'credit card ending <card_last4>',
                       'personal_loan': 'personal loan', 'car_loan': 'car loan'},
    'weekday_convention': {'this': 'current_week', 'next': 'following_week'},
    'proposal_date_rule': 'last_business_day_of_week',
    'promise_business_day_only': True,
    'callback': {'allowed_days': ['today', 'next_business_day'], 'start': '10:00', 'end': '19:00',
                 'must_be_after_now': True},
    'identity': {'questions': [{'field': 'date_of_birth', 'type': 'date'},
                               {'field': 'phone_last4', 'type': 'digits'}],
                 'max_wrong_answers': 3, 'numeric_date_order': 'DMY'},
    'sms_sentence': 'You will receive a text message confirming this promise.',
    'promise_retry_limit': 1,
}


def CC(dl, pd, mp, l4='0000'):
    return {'type': 'credit_card', 'card_last4': l4, 'past_due': pd, 'days_late': dl, 'minimum_payment': mp}


def LOAN(t, dl, pd, ia):
    return {'type': t, 'past_due': pd, 'days_late': dl, 'instalment_amount': ia}


def test_business_days():
    assert cr.is_business_day(D(2026, 10, 14), SPEC_A)
    assert not cr.is_business_day(D(2026, 10, 17), SPEC_A)
    assert not cr.is_business_day(D(2026, 10, 26), SPEC_A)
    assert cr.add_business_days(D(2026, 10, 14), 7, SPEC_A) == D(2026, 10, 23)
    assert cr.add_business_days(D(2026, 10, 14), 12, SPEC_A) == D(2026, 11, 2)
    assert cr.next_business_day_on_or_after(D(2026, 10, 26), SPEC_A) == D(2026, 10, 27)
    assert cr.last_business_day_of_week(D(2026, 10, 14), SPEC_A) == D(2026, 10, 16)
    assert cr.last_business_day_of_week(D(2026, 10, 14), SPEC_A, 1) == D(2026, 10, 23)
    # on a Friday attempt-1 goes to next week's last business day
    assert cr.default_proposal_date(D(2026, 10, 16), SPEC_A) == D(2026, 10, 23)
    assert cr.default_proposal_date(D(2026, 10, 14), SPEC_A) == D(2026, 10, 16)


def test_weekday_words():
    assert cr.resolve_weekday('this', 'Friday', D(2026, 10, 14), SPEC_A) == D(2026, 10, 16)
    assert cr.resolve_weekday('next', 'Friday', D(2026, 10, 14), SPEC_A) == D(2026, 10, 23)
    assert cr.resolve_weekday('next', 'Friday', D(2026, 10, 16), SPEC_A) == D(2026, 10, 23)  # rule 22
    alt = dict(SPEC_A, weekday_convention={'next': 'next_occurrence'})
    assert cr.resolve_weekday('next', 'Friday', D(2026, 10, 14), alt) == D(2026, 10, 16)


def test_bands_floor():
    assert cr.band_for(6, SPEC_A)['name'] == 'early'
    assert cr.band_for(8, SPEC_A)['name'] == 'late'
    assert cr.band_for(45, SPEC_A)['attempts'] == 2
    assert cr.floor_for(CC(12, 2125.1, 637.5), SPEC_A) == 637.5
    assert cr.floor_for(LOAN('car_loan', 14, 1250.0, 400.0), SPEC_A) == 400.0


def test_public_cases():
    # PUB-01: full amount today
    assert cr.promise_check(CC(6, 420.0, 126.0), '2026-10-14', 420.0, NOW, SPEC_A)['ok']
    # PUB-04: late band deadline 2026-10-23, 6 November rejected -> deadline offered
    car = LOAN('car_loan', 14, 1250.0, 400.0)
    assert cr.deadline_for(car, NOW, SPEC_A) == D(2026, 10, 23)
    r = cr.promise_check(car, '2026-11-06', 1250.0, NOW, SPEC_A)
    assert not r['ok'] and r['reason'] == 'after_deadline' and r['suggest_date'] == '2026-10-23'
    assert cr.promise_check(car, '2026-10-23', 1250.0, NOW, SPEC_A)['ok']
    # PUB-06: floor on this Friday
    cc6 = CC(12, 2125.1, 637.5)
    assert cr.promise_check(cc6, '2026-10-16', 637.5, NOW, SPEC_A)['ok']
    r = cr.promise_check(cc6, '2026-10-16', 500.0, NOW, SPEC_A)
    assert r['reason'] == 'below_floor' and r['suggest_amount'] == '637.50'
    # PUB-07: holiday 26 Oct -> offer 27 Oct, inside early deadline
    pl = LOAN('personal_loan', 5, 540.0, 180.0)
    r = cr.promise_check(pl, '2026-10-26', 540.0, NOW, SPEC_A)
    assert r['reason'] == 'not_business_day' and r['suggest_date'] == '2026-10-27'
    assert cr.promise_check(pl, '2026-10-27', 540.0, NOW, SPEC_A)['ok']
    # PUB-10: this Friday full amount
    assert cr.promise_check(CC(8, 365.0, 109.5), '2026-10-16', 365.0, NOW, SPEC_A)['ok']
    # PUB-11: all three this Friday
    for p in (CC(9, 220.0, 66.0), LOAN('personal_loan', 9, 640.0, 213.0), LOAN('car_loan', 3, 75.0, 25.0)):
        assert cr.promise_check(p, '2026-10-16', p['past_due'], NOW, SPEC_A)['ok']
    # PUB-12: credit card tomorrow; attempts 2 (late) and 1 (early)
    assert cr.promise_check(CC(16, 510.0, 153.0), '2026-10-15', 510.0, NOW, SPEC_A)['ok']
    assert cr.attempts_for(LOAN('personal_loan', 16, 1320.0, 440.0), SPEC_A) == 2
    assert cr.attempts_for(LOAN('car_loan', 7, 140.0, 46.0), SPEC_A) == 1
    # PUB-13: card early -> 30 Oct ok; loan late -> deadline 23 Oct
    assert cr.promise_check(CC(4, 300.0, 90.0), '2026-10-30', 300.0, NOW, SPEC_A)['ok']
    r = cr.promise_check(LOAN('personal_loan', 20, 900.0, 300.0), '2026-10-30', 900.0, NOW, SPEC_A)
    assert r['reason'] == 'after_deadline' and r['suggest_date'] == '2026-10-23'
    # weekend + past
    assert cr.promise_check(pl, '2026-10-17', 540.0, NOW, SPEC_A)['suggest_date'] == '2026-10-19'
    assert cr.promise_check(pl, '2026-10-13', 540.0, NOW, SPEC_A)['reason'] == 'before_earliest'


def test_callback():
    assert cr.callback_slot_valid('2026-10-15', '11:00', NOW, SPEC_A)['ok']  # PUB-02
    assert cr.callback_slot_valid('2026-10-14', '19:00', NOW, SPEC_A)['ok']
    assert cr.callback_slot_valid('2026-10-14', '10:30', NOW, SPEC_A)['reason'] == 'not_after_now'
    assert cr.callback_slot_valid('2026-10-15', '19:30', NOW, SPEC_A)['reason'] == 'time_outside_window'
    assert cr.callback_slot_valid('2026-10-16', '11:00', NOW, SPEC_A)['reason'] == 'day_not_allowed'
    # Friday 23 Oct -> next business day skips weekend and the 26th holiday -> Tue 27
    assert cr.callback_slot_valid('2026-10-27', '10:00', '2026-10-23T12:00', SPEC_A)['ok']


def test_normalize_dob():
    assert cr.normalize_date_answer('14 March 1988') == '1988-03-14'
    assert cr.normalize_date_answer('March 14th, 1988') == '1988-03-14'
    assert cr.normalize_date_answer('03/04/1988') == '1988-04-03'  # day first
    assert cr.normalize_date_answer('1988-03-14') == '1988-03-14'
    assert cr.normalize_date_answer('the twelfth') == 'the twelfth'


def _no_braces(code):
    assert '{{' not in code and '}}' not in code


def test_portable_has_no_double_braces():
    _no_braces(cr.portable_source())


def _get_account_data(products):
    out = []
    for i, p in enumerate(products):
        q = dict(p)
        q['product_id'] = 'p' + str(i + 1)
        out.append(q)
    return dict(ok=True, products=out)


def test_date_facts_code_runs_all_input_shapes():
    code = codegen.emit_date_facts_code(SPEC_A)
    _no_braces(code)
    prods = [CC(4, 300.0, 90.0, '6604'), LOAN('personal_loan', 20, 900.0, 300.0)]
    data = _get_account_data(prods)
    shapes = [
        dict(now=NOW, products=data['products']),                       # mapped list
        dict(now=NOW, products=json.dumps(data['products'])),           # JSON string
        dict(now=NOW, products=str(data['products'])),                  # python repr string
    ]
    flat = dict(now=NOW)
    for i, p in enumerate(data['products']):
        for k, val in p.items():
            flat['get_account_response.data.products.' + str(i) + '.' + k] = str(val)
    shapes.append(flat)
    for v in shapes:
        exec(code, dict(vars=v))
        assert v['p1_deadline'] == '2026-11-02', v.get('p1_deadline')
        assert v['p2_deadline'] == '2026-10-23'
        assert v['p1_floor'] == '90.00' and v['p2_floor'] == '300.00'
        assert v['p1_band'] == 'early' and v['p2_attempts'] == '2'
        assert v['p1_label'] == 'credit card ending 6604'
        assert v['attempt1_date'] == '2026-10-16'
        assert 'Friday 23 October 2026' in v['date_facts']
        assert '2026-10-26 Monday: NOT a business day (bank holiday)' in v['date_facts']
        assert '"next Friday" = Friday 23 October 2026' in v['date_facts']
    # separate globals/locals (sandbox variant) and nothing loaded yet
    v = dict(now=NOW)
    exec(code, dict(), dict(vars=v))
    assert v['n_products'] == '0' and 'TODAY is Wednesday 14 October 2026' in v['date_facts']
    assert v['callback_dates'] == '2026-10-14, 2026-10-15'
    assert all(isinstance(x, str) for x in v.values())
    # garbage never raises
    v = dict(now=None, products='not json')
    exec(code, dict(vars=v))
    assert 'date_facts' in v


def test_hooks():
    hooks = [codegen.emit_get_account_post_hook(SPEC_A), codegen.emit_verify_identity_post_hook(SPEC_A),
             codegen.emit_create_promise_post_hook(SPEC_A), codegen.emit_verify_identity_pre_hook(SPEC_A),
             codegen.emit_generic_post_hook()]
    for h in hooks:
        _no_braces(h)
    # get_account post hook
    v = dict(now=NOW)
    res = dict(status='success', data=_get_account_data([LOAN('car_loan', 14, 1250.0, 400.0)]), header=dict(a=1))
    exec(hooks[0], dict(result=res, vars=v))
    p = res['data']['products'][0]
    assert p['latest_promise_date'] == '2026-10-23' and p['floor_amount'] == 400.0 and 'header' not in res
    assert v['p1_deadline'] == '2026-10-23' and 'what_to_do_next' in res['data']
    exec(hooks[0], dict(result=dict(data='broken')))  # vars missing -> builtin vars, no crash
    # verify_identity post hook
    for data, expect in [
        (dict(ok=True, verified=True, all_verified=True), 'IDENTITY VERIFIED'),
        (dict(ok=True, verified=True, all_verified=False), 'NEXT security question'),
        (dict(ok=True, verified=False, wrong_answers_left=2), '2 wrong answer(s) left'),
        (dict(ok=True, verified=False, wrong_answers_left=0), 'FAILED'),
        (dict(ok=True, verified=False, wrong_answers_left=2, hint='day_month_swapped'), 'month as a word'),
        (dict(ok=False, error='unreadable date'), 'could not be read'),
    ]:
        r = dict(status='success', data=data)
        exec(hooks[1], dict(result=r))
        assert expect in r['data']['what_to_do_next'], (data, r['data']['what_to_do_next'])
    # create_promise post hook: fail, fail, then ok
    v = dict()
    r1 = dict(status='error', status_code=500, data='Internal error')
    exec(hooks[2], dict(result=r1, vars=v))
    assert 'Call create_promise again' in r1['data']['what_to_do_next']
    r2 = dict(status='success', status_code=200, data=dict(ok=False, error='x'))
    exec(hooks[2], dict(result=r2, vars=v))
    assert 'NOT recorded again' in r2['data']['what_to_do_next']
    r3 = dict(status='success', status_code=200, data=dict(ok=True, promise_id='pr1'))
    exec(hooks[2], dict(result=r3, vars=dict()))
    assert 'text message confirming' in r3['data']['what_to_do_next']
    assert 'IS recorded' in r3['data']['what_to_do_next']
    # verify_identity pre hook normalises answers
    cfg = dict(url='u', method='POST', body=dict(customer_id='c', field='date_of_birth', answer='14 March 1988'))
    exec(hooks[3], dict(config=cfg, vars=dict()))
    assert cfg['body']['answer'] == '1988-03-14'
    cfg = dict(body=dict(customer_id='c', field='phone_last4', answer='4 4 7 1'))
    exec(hooks[3], dict(config=cfg, vars=dict()))
    assert cfg['body']['answer'] == '4471'


if __name__ == '__main__':
    n = 0
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn()
            n += 1
            print('ok', name)
    print(n, 'tests passed')
