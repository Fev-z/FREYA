import json, sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src).read()
d = json.loads(s)
N = d['nodes']
def code(n): return N[n]['pre_actions'][0]['function']['parameters']['properties']['code']

# ---- setup code: Turkish names, hitap, holidays from takvim.md + duyurular 2026-10-02
c = code('setup')['default']
assert "HOL = ['2026-10-26', '2026-11-11', '2026-11-26', '2026-12-25', '2027-01-01']" in c
c = c.replace("    def sp(d):\n        return d.strftime('%A') + ' ' + str(d.day) + ' ' + d.strftime('%B') + ' ' + str(d.year)",
"    TRD = ['Pazartesi','Salı','Çarşamba','Perşembe','Cuma','Cumartesi','Pazar']\n    TRM = ['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık']\n    def sp(d, TRD=TRD, TRM=TRM):\n        return str(d.day) + ' ' + TRM[d.month-1] + ' ' + str(d.year) + ' ' + TRD[d.weekday()]")
c = c.replace("x.isoformat() + ' ' + x.strftime('%A') + ': ' + tag", "x.isoformat() + ' ' + TRD[x.weekday()] + ': ' + tag")
c = c.replace("names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']", "names = TRD")
c = c.replace("wk.append('this ' + names[i] + ' = ' + a.isoformat() + (' (past)' if a < today else '') + '; next ' + names[i] + ' = ' + b2.isoformat())",
              "wk.append('\"bu ' + names[i] + '\" = ' + a.isoformat() + (' (geçmiş)' if a < today else '') + '; \"haftaya ' + names[i] + '\" = ' + b2.isoformat())")
c = c.replace("' (' + nbd_after.strftime('%A') + ')", "' (' + TRD[nbd_after.weekday()] + ')")
c = c.replace("    vars['today_iso'] = today.isoformat()\n",
"    vars['today_iso'] = today.isoformat()\n    fn = str(vars.get('first_name') or '').strip()\n    vars['hitap'] = fn + (' Hanım' if str(vars.get('title') or '').strip().lower() in ('ms','mrs','miss') else ' Bey')\n    vars['tomorrow_iso'] = (today + one).isoformat()\n", 1)
c = c.replace("    vars['setup_state'] = 'error'\n", "    vars['setup_state'] = 'error'\n    vars['hitap'] = str(vars.get('first_name') or '') + (' Hanım' if str(vars.get('title') or '') == 'Ms' else ' Bey')\n")
assert 'TRD[x.weekday()]' in c and "vars['hitap']" in c and 'haftaya' in c
code('setup')['default'] = c

# ---- account facts: Turkish product words and statements
c = code('account_facts')['default']
reps = [
("            words = 'credit card ending ' + str(p.get('card_last4') or '')", "            words = str(p.get('card_last4') or '') + ' ile biten kredi kartınız'"),
("            words = 'car loan'", "            words = 'taşıt krediniz'"),
("            words = 'personal loan'", "            words = 'ihtiyaç krediniz'"),
("            floor_name = 'minimum payment'", "            floor_name = 'asgari ödeme'"),
("            floor_name = 'instalment amount'", "            floor_name = 'taksit tutarı'"),
("""    def money(x):
        x = round(float(x), 2)
        if abs(x - int(x)) < 0.001:
            return '{:,}'.format(int(x))
        return '{:,.2f}'.format(x)""", """    def money(x):
        x = round(float(x), 2)
        if abs(x - int(x)) < 0.001:
            return str(int(x)) + ' lira'
        kr = int(round((x - int(x)) * 100))
        return str(int(x)) + ' lira ' + str(kr) + ' kuruş'"""),
("""    def sp(iso, dt=dt):
        d = dt.date.fromisoformat(iso)
        return d.strftime('%A') + ' ' + str(d.day) + ' ' + d.strftime('%B')""", """    def sp(iso, dt=dt):
        TRD = ['Pazartesi','Salı','Çarşamba','Perşembe','Cuma','Cumartesi','Pazar']
        TRM = ['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık']
        d = dt.date.fromisoformat(iso)
        return str(d.day) + ' ' + TRM[d.month-1] + ' ' + TRD[d.weekday()]"""),
("        stmts.append('your ' + words + ' has a past-due amount of ' + money(due) + ' and is ' + str(late) + ' days late')",
 "        stmts.append(words + ' için gecikmiş tutar ' + money(due) + ', ödeme ' + str(late) + ' gün gecikmiş')"),
("        vars['debt_statement'] = 'I am calling from the collections team about a late payment: ' + stmts[0] + '.'",
 "        vars['debt_statement'] = 'Tahsilat ekibinden, gecikmiş bir ödeme için arıyorum: ' + stmts[0] + '.'"),
("        vars['debt_statement'] = 'I am calling from the collections team about late payments. ' + ' '.join(s[0].upper() + s[1:] + '.' for s in stmts)",
 "        vars['debt_statement'] = 'Tahsilat ekibinden, gecikmiş ödemeler için arıyorum. ' + ' '.join(s[0].upper() + s[1:] + '.' for s in stmts)"),
("    vars['today_question'] = 'Can you make this payment today?' if len(stmts) == 1 else 'Can you pay all of them today?'",
 "    vars['today_question'] = 'Bu ödemeyi bugün yapabilir misiniz?'"),
("    vars['today_question'] = 'Can you make this payment today?'", "    vars['today_question'] = 'Bu ödemeyi bugün yapabilir misiniz?'"),
]
for a,b in reps:
    assert a in c, a[:60]
    c = c.replace(a,b)
code('account_facts')['default'] = c

# ---- verify pre: Turkish months
t = N['identity']['tools'][0]
p = t['pre_process_code']
a = "months = ['january','february','march','april','may','june','july','august','september','october','november','december']"
assert a in p
p = p.replace(a, "months = ['ocak','şubat','mart','nisan','mayıs','haziran','temmuz','ağustos','eylül','ekim','kasım','aralık']")
p = p.replace("if months[i] in low or re.search(r'\\b' + months[i][:3] + r'\\b', low):", "if months[i] in low or months[i].replace('ş','s').replace('ı','i').replace('ğ','g').replace('ü','u') in low:")
t['pre_process_code'] = p
t['post_process_code'] = t['post_process_code'].replace('for example 14 March 1988', 'for example "on dört Mart bin dokuz yüz seksen sekiz"')

s = json.dumps(d, ensure_ascii=False)
s = s.replace('{{title}} {{last_name}}', '{{hitap}}')
d = json.loads(s)
N = d['nodes']

d['system_prompt'] = d['system_prompt'].replace('Speak English. Keep every turn', 'Speak ONLY Turkish (Türkçe) for the whole call, every sentence. Keep every turn').replace('Address the customer as {{hitap}}.', 'Address the customer as "{{hitap}}". Amounts are Turkish lira: say them in words a person understands (e.g. "dört yüz yirmi lira"), and dates as day, month name and weekday (e.g. "16 Ekim Cuma"), never ISO format.') + """
Fixed Turkish sentences (say exactly):
- robot / yapay zekâ question: "Ben Freya Bank'ın dijital asistanıyım." then continue.
- scam question: "Bu aramayı Freya Bank müşteri hizmetleri numarasını arayarak doğrulayabilirsiniz." then continue.
- unknown information: "Bu bilgiye sahip değilim."
- goodbye: "Zaman ayırdığınız için teşekkür ederim, iyi günler." """

OPEN = "Merhaba, ben Freya Bank'ın dijital asistanıyım. Bu görüşme kaydedilmektedir. {{hitap}} ile mi görüşüyorum?"
idn = N['identity']
old_open = idn['on_enter']['text']
idn['on_enter']['text'] = OPEN
idn['task_message'] = idn['task_message'].replace(old_open, OPEN)
tm = idn['task_message']
tm = tm.replace('never mention collections, a debt, a payment, an amount or a product, to anyone', 'never say "tahsilat", "borç", "ödeme", an amount or a product, to anyone (relatives included)')
tm = tm.replace('Only "yes", "that\'s me", "speaking" or the customer saying their own name confirms it. "Hello", "go ahead", "who is this" do NOT confirm.', 'Only "evet", "benim", "buyurun benim" or the customer saying their own name confirms it. "Alo", "buyurun", "kimsiniz" do NOT confirm.')
tm = tm.replace('ask once more "Am I speaking with {{hitap}}?"', 'ask once more "{{hitap}} ile mi görüşüyorum?"')
tm = tm.replace('say exactly "I am sorry for your loss."', 'say exactly "Başınız sağ olsun."')
tm = tm.replace('(for "around eleven" use 11:00)', '(for "on bir gibi" / "around eleven" use 11:00; "yarın" = {{tomorrow_iso}})')
tm += '\n\nSpeak Turkish. Security questions in Turkish, e.g. "Doğum tarihinizi söyler misiniz?" and then "Dosyadaki telefon numaranızın son dört hanesini söyler misiniz?". Turkish dates: "on dört Mart seksen sekiz" -> 1988-03-14.'
idn['task_message'] = tm

N['identity_failed']['on_enter']['text'] = "Üzgünüm, kimliğinizi doğrulayamadım. Lütfen Freya Bank mobil uygulamasını kullanın ya da bir şubeye uğrayın. Zaman ayırdığınız için teşekkür ederim, {{hitap}}. İyi günler."
N['account_error']['on_enter']['text'] = "Teşekkürler, kimliğiniz doğrulandı. Üzgünüm, teknik bir sorun nedeniyle şu anda hesap bilgilerinize ulaşamıyorum, bugün devam edemiyorum. Zaman ayırdığınız için teşekkür ederim, {{hitap}}. İyi günler."
N['negotiate']['on_enter']['text'] = "Teşekkür ederim, {{hitap}}. {{debt_statement}} {{today_question}}"
ng = N['negotiate']['task_message']
ng = ng.replace('asked "Can you make this payment today?"', 'asked "Bu ödemeyi bugün yapabilir misiniz?"')
ng = ng.replace('Vague period ("next week", "end of the month", "when my salary comes", "the week after next")', 'Vague period ("haftaya", "ay sonu", "maaşım yatınca", "önümüzdeki hafta")')
ng = ng.replace('"next <weekday>" = that weekday in the following calendar week; "this <weekday>" = the one in the current week (use the weekday words above). "tomorrow" = the day after today.', '"haftaya <gün>" = that weekday in the following calendar week; "bu <gün>" = the one in the current week (use the weekday words above). "yarın" = the day after today, "öbür gün" = two days after today.')
ng = ng.replace('for example "Friday 16 October"', 'for example "16 Ekim Cuma"')
ng = ng.replace('ask "Do you confirm?"', 'ask "Onaylıyor musunuz?"')
ng = ng.replace('"I already paid"', '"Zaten ödedim"').replace('"This debt is not mine", "I never had this product"', '"Bu borç benim değil", "Böyle bir ürünüm hiç olmadı"')
ng += '\n\nSpeak Turkish. Never ask "ne kadar ödeyebilirsiniz?". Turkish amounts: "dört yüz elli" = 450, "bin iki yüz" = 1200, "yüz yirmi beş buçuk" = 125.5. A self-correction ("21, pardon 20") means the latest value.'
N['negotiate']['on_enter_note'] = None
del N['negotiate']['on_enter_note']
N['negotiate']['task_message'] = ng
N['promise_done']['on_enter']['text'] = "Teşekkürler, sözünüz kaydedildi. Bu sözü onaylayan bir kısa mesaj alacaksınız. Size yardımcı olabileceğim başka bir konu var mı?"
N['promise_done']['task_message'] += '\nSpeak Turkish.'
d['test_variables'] = {'customer_id': 'c_test', 'first_name': 'Daniel', 'last_name': 'Reyes', 'title': 'Mr', 'now': '2026-10-14T11:00'}
d.pop('agent_config', None)
out = json.dumps(d, ensure_ascii=False, indent=1)
assert 'null' not in out.replace('"null"','')
open(dst,'w').write(out)
print('ok', list(N))
