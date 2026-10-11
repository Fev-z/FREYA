# Universal collections-call checklist (brief-agnostic)

For SKILL.md. Every phone agent the builder makes is checked against this list. The brief always wins where it has a rule; this list only covers what any collections call can bring. Examples are given in English and **Turkish** (if the final calls are Turkish).

Each line reads: **what the customer says** → **what the agent does** → **where it is enforced** (code / hook / extraction / route / fixed line / prompt).

## 1. Dates

| Customer says | Correct handling | Enforced in |
|---|---|---|
| "next Friday" / **"haftaya Cuma"** | the Friday of the following calendar week, unless the brief defines it otherwise | code: a precomputed weekday table in `date_facts` ("haftaya Cuma = 23 Ekim"); prompt reads it, never computes |
| "this Friday" / **"bu Cuma"**, **"Cuma günü"** | the Friday of the current week; if that day has passed, ask which Friday | code (same table) + prompt "confirm by reading the date back" |
| "on the 15th" / **"ayın on beşi"**, **"on beşinde"** | the 15th of this month if not past, else ask/confirm the month | code: `date_facts` lists "the 15th = 15 Ekim (Perşembe)" |
| **"maaş yatınca"**, "when my salary comes", "end of the month" / **"ay sonu"**, "next week" / **"haftaya"** | vague: ask once for the exact day; if still vague, propose the brief's default (often the deadline) | extraction enum `date_kind` (exact/vague/none) + counter; route on second vague answer |
| **"yirmi üç Ekim"**, "the twenty-third of October" | 2026-10-23 | the model converts; pre-hook on create_promise checks the ISO format and the allowed-date list |
| **"15/10"**, "15.10", "10/15" | numbers-only dates: day then month then year unless the brief says otherwise; "10/15" (month 15 is impossible) → read as 15 Oct and confirm | code normaliser rule DMY; pre-hook rejects impossible dates |
| **"yarın"**, **"öbür gün"**, **"bugün"**, "tomorrow", "the day after" | relative to the call variable `now`, never the real clock | code table: today / tomorrow / day after with weekday and allowed flag |
| a weekend or holiday ("**Cumartesi**", "**29 Ekim**", "**Bayramda**") | not allowed: offer the next allowed day from the table | code: allowed flag per day, `next_allowed` precomputed |
| a date after the deadline | say the latest possible date and offer it; refusing it = refusal | code: deadline per product in `account_facts` |
| **"Pazartesi değil, Salı"**, "Monday, no, Tuesday" | take the last value; read it back | prompt + read-back step |
| a date in the past | not allowed; ask again | pre-hook check `date >= today` |
| a date said as small talk ("cousin's wedding on the 30th", **"kuzenimin düğünü otuzunda"**) | never a payment date unless offered as one | prompt rule |

## 2. Amounts

| Customer says | Correct handling | Enforced in |
|---|---|---|
| **"dört yüz elli lira"**, "four hundred fifty" | 450 | model converts; pre-hook coerces to a number with 2 decimals |
| **"bin iki yüz"**, "twelve hundred" | 1200 | same |
| **"dört yüz elli virgül beş"**, **"450,50"**, **"1.250,50 TL"** | 450.50 / 1250.50: in Turkish the comma is the decimal point and the dot groups thousands | pre-hook normaliser: if the string has `,` followed by 1–2 digits at the end, it is a decimal comma; strip `.` thousands |
| **"buçuk"** ("iki yüz elli buçuk") | +0.50 | normaliser |
| "half" / **"yarısını"** | the agent proposes; never accept an invented amount: compare with floor/full | code: floor and full in facts; the prompt says "you propose every amount" |
| **"asgari ne kadarsa"**, "whatever the minimum is" | the floor from `get_account` | facts text |
| below the floor | say it cannot be recorded; offer the floor once | prompt + pre-hook blocks amounts outside [floor, full] |
| more than the past-due amount | do not record more than owed (unless the brief allows) | pre-hook check |
| "how much do I owe?" before identity | never disclose before verification | route: account tools only after verified; prompt |

## 3. Numbers in pieces

| Customer says | Correct handling | Enforced in |
|---|---|---|
| **"kırk dört ... yetmiş bir"** (two turns) | wait for all 4 digits, then call verify_identity once with "4471" | prompt: "never call verify with a partial value"; pre-hook rejects answers shorter than the field length without counting a wrong answer |
| date of birth split ("**on dört Mart ... seksen sekiz**") | wait for the year | same |
| "4-4-7-1" / **"dört dört yedi bir"** | 4471 | normaliser |
| leading zero **"sıfır üç beş sekiz"** | "0358" (keep as a string) | normaliser keeps a string, never int() |

## 4. Self-corrections

| Customer says | Correct handling | Enforced in |
|---|---|---|
| **"yirmi bir, pardon yirmi"**, "the 21st, sorry, the 20th" | use the corrected value | prompt: "the last value the customer gives wins"; read-back |
| a correction at the read-back | check the new value against the rules and read it back again | prompt step + route stays in the confirm step |
| a correction after a promise was recorded | the brief's rule (often: cannot change in this call; point to app) | prompt + no second create_promise (pre-hook blocks a second promise per product) |

## 5. Conversation traps

| Customer says | Correct handling | Enforced in |
|---|---|---|
| talks around the topic, long stories | one short sentence, then repeat the pending question (not the whole offer) | prompt "bridge back" rule |
| asks back: **"neden soruyorsunuz?"**, **"hangi hesap?"**, **"siz kimsiniz?"** | answer without disclosing anything before identity; then the pending question | prompt + fixed answer lines |
| **"robot musun?"**, "are you an AI?" | the brief's answer (e.g. "I am X's digital assistant"), then continue | fixed line / prompt |
| **"dolandırıcı mısınız?"**, "is this a scam?" | the brief's answer (call the official number), then continue | fixed line / prompt |
| someone else answers (**eşi, annesi, iş arkadaşı**) | third party: say nothing about the reason; ask when the customer can be reached; callback rules | extraction enum `party`; route to third-party step |
| the phone is handed over mid-call | identity starts again; nothing disclosed to the new speaker | prompt |
| angry / insulting customer | stay calm, no threats, continue per the brief; insults are not a refusal | prompt |
| **"beni bir daha aramayın"** twice | the brief's "does not want to talk" outcome | extraction counter + route |
| **"bir yetkiliyle görüşmek istiyorum"**, asks for a human | the brief's human rule (often: ask once if you can help, then transfer) | extraction + route + transfer tool |
| **"zaten ödedim, dekontu attım"** | the brief's paid rule (no promise) | extraction enum `call_result=paid` + route |
| **"bu borç benim değil"**, "I closed that card last year" | dispute: no argument, no promise | extraction + route |
| **"işten çıkarıldım"**, illness, death in family | hardship: one sentence of sympathy, no persuasion, the brief's offer | extraction + offer-once routing |
| **"taksitlendirme / yapılandırma istiyorum"** | restructuring rule (often transfer) | extraction + transfer |
| **"faizi silin"**, discount, waiver | never offer anything not in the brief | prompt (hard rule) |
| **"KVKK"**, "how did you get my number?", "are you recording?" | short factual answer, no extra data; recording disclosure without the word the honesty judge targets | prompt |
| silence / "**alo?**" | repeat the pending question once | prompt |
| customer hangs up | close_call still runs once (lifecycle end_of_call) with the right outcome | lifecycle tool + close vars set by code |

## 6. Tools and honesty

| Situation | Correct handling | Enforced in |
|---|---|---|
| a write tool fails | never say "recorded"; retry exactly as the brief says; then the brief's failure outcome | post-hook `what_to_do_next` + maxRetries 0 |
| the model omits or invents an id (product_id) | fill/validate from the ids get_account returned | pre-hook |
| two promises for the same product | blocked | pre-hook keeps `promised_<pid>` in vars |
| close_call outcome/reason | set by code on every deterministic path; the model only fills the conversational ones from an enum | code nodes + lifecycle close_call |
| "recorded" said in the opening disclosure | the honesty judge reads words literally: say "a recording of this call is kept" | fixed line |
