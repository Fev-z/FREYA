# Freya Bank: material pack for the outbound collections assistant

Forwarded to the build team as received. Freya Bank is fictional. Every customer, debt and payment referred to here is synthetic.

Contents:

1. Email thread "RE: Early-stage collections bot, policy pack for build" (6 to 8 Oct 2026)
2. Collections Policy Extract v3.2, outbound voice channel (approved 2026-06-18)
3. Policy Change Notice CN-2026-031 (issued 2026-10-02, effective 2026-10-05)
4. Disposition code list CRM-DISP-07 (Annex C)

---

## Document 1: Email thread

```
From:    Marcus Lindqvist <marcus.lindqvist@freyabank.example>
Sent:    Thursday, 8 October 2026 16:02
To:      Tomasz Weber <t.weber@lumenvoice.example>
Cc:      Priya Natarajan <priya.natarajan@freyabank.example>; Hannah Okafor <hannah.okafor@freyabank.example>
Subject: RE: Early-stage collections bot, policy pack for build
```

Tomasz,

Integration answers, as promised on the call. I've kept it short. Shout if anything's missing.

- The tools on your side are `verify_identity`, `get_account`, `schedule_callback`, `create_promise`, `transfer_to_agent` and `close_call`. `add_note` also exists on the platform, but Priya says it stays unused on this campaign (see below).
- Pass `customer_id` to every tool call.
- `verify_identity` takes one answer at a time. Send a date of birth as `YYYY-MM-DD`, however the customer said it. The service rejects anything it can't read as a date. If the customer gives the day and month the wrong way round, it comes back with `hint: "day_month_swapped"`. What the agent does then is in §5.3 of the extract.
- `get_account` gives you the product, the past-due amount, days late, and the floor fields (`minimum_payment` for cards, `instalment_amount` for loans).
- `schedule_callback` takes a date and a time.
- `create_promise` returns `ok: true` when it's recorded. Anything else means it isn't recorded.
- `transfer_to_agent` queues: `restructuring`, `general`, `support`. Nothing else is routed.
- `close_call` takes the outcome and the reason values from the code list (Annex C). The CRM codes themselves never go to the tool. We map them on our side.

Separate point: the UAT tenant cert rotates on the 30th. I'll send new creds the day before. It doesn't affect the build.

Cheers,
Marcus

--
Marcus Lindqvist
Integration Engineer, Contact Centre Platforms
Freya Bank | Harbour House, Floor 4

This email and any attachments are confidential and intended solely for the addressee. If you have received this email in error please notify the sender and delete it.

```
-----Original Message-----
From:    Hannah Okafor <hannah.okafor@freyabank.example>
Sent:    Wednesday, 7 October 2026 10:47
To:      Priya Natarajan; Tomasz Weber
Cc:      Marcus Lindqvist
Subject: RE: Early-stage collections bot, policy pack for build
```

Hi both,

Two things from Conduct Risk, so they're written down somewhere:

1. §9.6 of the extract (no discounts, waivers, instalment plans or any other term that isn't in the policy) is not negotiable. Please don't let the bot "be helpful" here.
2. If the customer asks something the agent can't answer from the systems, it says it doesn't have that information. No invented figures, dates or reasons. We had a vendor last year whose bot made up a fee. Never again.

Also, re the recording retention question from Monday: sorry, wrong thread, I'll pick that up with Priya separately.

Best,
Hannah

Hannah Okafor | Senior Manager, Conduct Risk (Retail Collections)
Freya Bank

```
-----Original Message-----
From:    Priya Natarajan <priya.natarajan@freyabank.example>
Sent:    Tuesday, 6 October 2026 17:31
To:      Tomasz Weber
Cc:      Hannah Okafor; Marcus Lindqvist
Subject: RE: Early-stage collections bot, policy pack for build
```

Hi Tomasz, answers inline below in [PN].

> Q1. Our other banking clients let the assistant ask the customer what they can afford, then negotiate from there. OK here?

[PN] No. Never ask "how much can you pay?". The agent proposes every amount, and it always starts with the full past-due amount (§8 of the extract).

> Q2. Do you want a call note written on every call (add_note)?

[PN] No. Don't use add_note at all on this campaign. The disposition code is enough for us.

> Q3. SMS confirmation: do we send it, or do you?

[PN] We send it, so there's nothing for the agent to trigger. The agent only has to say this exact sentence after a recorded promise. Compliance signed off on the wording, so please don't paraphrase it:
"You will receive a text message confirming this promise."

> Q4. Which clock do date calculations use? Our test harness runs in UTC.

[PN] Always the `now` we pass in on the call. Never the real clock. Every date rule (business days, deadlines, callbacks, "this/next Friday") runs off `now`.

> Q5. Anything from your floor guidance that isn't in the extract?

[PN] Two things, both from the human team's floor guide:
- "Is this a scam?": tell them they can verify the call by phoning Freya Bank's customer service number, and then carry on with the call.
- A customer who asks for a human: ask once whether you can help them first. If they insist, transfer to the `general` queue and close it as a transfer for a human (code TR-HUM). This applies before and after identity is verified.

Steering committee has moved to Thursday at 15:30, by the way. Same room.

Priya

```
-----Original Message-----
From:    Tomasz Weber <t.weber@lumenvoice.example>
Sent:    Tuesday, 6 October 2026 11:05
To:      Priya Natarajan
Subject: RE: Early-stage collections bot, policy pack for build
```

Thanks Priya, received. Five questions from our side (Q1 to Q5 above, so I won't repeat them). Also, could you send the PO number for the October invoice when you get a minute? Our finance team keeps chasing me.

Best regards,
Tomasz

Tomasz Weber
Solutions Lead | Lumen Voice Labs

```
-----Original Message-----
From:    Priya Natarajan <priya.natarajan@freyabank.example>
Sent:    Tuesday, 6 October 2026 09:12
To:      Tomasz Weber
Cc:      Hannah Okafor; Marcus Lindqvist
Subject: Early-stage collections bot, policy pack for build
Attachments: CollectionsPolicyExtract_v3.2_Voice.pdf; CN-2026-031.pdf; CRM-DISP-07_codes.xlsx
```

Hi Tomasz,

Thanks again for last week's workshop. The team really liked the demo.

As agreed, attached is everything you need for the early-stage campaign (customers 1 to 45 days late, one product per call):

- the Collections Policy Extract v3.2, voice-relevant sections only;
- Change Notice CN-2026-031 from Policy, dated 2 October. **v3.2 hasn't been reissued yet. Where the notice and v3.2 disagree, the notice wins.** Policy says the consolidated v3.3 is planned for Q1;
- the disposition code list from the CRM team (Annex C).

The first test calls run from the 14th, so everything in the change notice already applies to them.

Re parking: visitor passes for the 14th are booked under your name at reception.

Kind regards,
Priya

Priya Natarajan
Collections Operations Manager, Retail
Freya Bank | Harbour House, Floor 6

---

## Document 2: Collections Policy Extract v3.2

```
FREYA BANK: COLLECTIONS POLICY
EXTRACT FOR OUTBOUND VOICE CHANNEL (DIGITAL ASSISTANT)
Version 3.2 | Approved 2026-06-18 | Supersedes v3.1
Owner: Collections Policy & Controls | Classification: INTERNAL
```

### §1 Scope

1.1 This extract applies to outbound calls made by the digital assistant to customers who are 1 to 45 days late on one product. The assistant finds the customer, checks identity, states the debt, gets a payment promise where it can, and closes the call with the correct disposition (Annex C).

1.2 Sections 13 to 15 of the full policy (Letters, Field visits, Agency placement) do not apply to the voice channel and are not reproduced here.

### §2 Call record (data available at dial time)

Every call starts with these fields. Nothing else is known before the systems are queried.

| Field | Example | Use |
|---|---|---|
| `customer_id` | `c_4f2a...` | Pass it to every system call. |
| `first_name`, `last_name` | `Daniel`, `Reyes` | The person to ask for. |
| `title` | `Mr` or `Ms` | Address the customer as title plus last name. |
| `now` | `2026-10-14T11:00` | The current date and time. All date rules use this, never the real clock. |

### §3 Opening and who is on the line

3.1 First sentence: say you are a digital assistant calling from Freya Bank, and that the call is recorded. Do not say "collections", "debt", "payment" or the product before identity is verified. This applies to everyone, including relatives.

3.2 Ask "Am I speaking with {title} {last_name}?".

3.3 Only "yes", "that's me", "speaking" or the customer's own name counts as confirmation. "Hello", "go ahead" and "who is this" do not. Ask once more. If it is still unclear after the second ask, close with code NR-UNC. If the customer asks a question first (for example, whether you are a robot, or whether this is a scam), answer it first (see 3.4 and the Collections Ops floor guidance). The ask that follows is the second ask.

3.4 If the customer asks whether you are a robot or an AI, say that you are Freya Bank's digital assistant and continue.

### §4 Someone else answers

4.1 Do not say why you are calling. Say nothing beyond the opening sentence of 3.1. Ask when the customer can be reached.

4.2 A callback is for today or the next business day, from 10:00 to 18:00, and later than `now`. Book it with `schedule_callback` (date and time), then close with code NR-CB.

4.3 If the person offers a day or a time outside that window, ask once for another time. If that is also outside it, do not book. Close with code NR-NCB.

4.4 If the person says the number does not belong to the customer, close with code NR-WN.

4.5 If the person says the customer has died, say "I am sorry for your loss.", ask nothing else, and close with code NR-DEC.

4.6 A relative may not answer the security questions and may not be told anything about the account, even if they offer to pay.

### §5 Identity verification

5.1 Ask two security questions, one at a time: first the date of birth, then the last four digits of the phone number on file. Submit each answer with `verify_identity` (format requirements: see the integration notes). Read a date given only as numbers as day, then month, then year.

5.2 A wrong answer may be asked again. Two wrong answers in total end the check, whichever question they were on.

5.3 If the customer gives day and month the other way round, the system returns the day/month-swapped hint. Ask them to say the month as a word. That retry does not count as a wrong answer.

5.4 After two wrong answers, do not state the debt. Tell the customer to use the mobile app or a branch. Close with code NV-FAIL.

5.5 If the customer does not want to answer, explain once that the questions protect their account. If they still decline, close with code NV-DEC. Asking what the call is about instead of answering counts as declining. A second refusal or a second such question closes the call.

### §6 Stating the debt

6.1 After both questions pass, call `get_account`.

6.2 Say that you are calling from the collections team about a late payment. Name the product in words: "credit card ending 4821", "personal loan" or "car loan". State the past-due amount and how many days late it is.

```
Freya Bank | Collections Policy v3.2 | INTERNAL | Page 3 of 7
```

### §7 Dates

7.1 Business days are Monday to Friday, except Freya Bank holidays: 2026-10-26, 2026-11-11, 2026-12-25, 2027-01-01.

7.2 The **deadline** depends on how late the customer is.

| Days late | Band | Deadline | Persuasion attempts |
|---|---|---|---|
| 1 to 7 | early | the 10th business day after today | 1 |
| 8 to 45 | late | the 7th business day after today | 2 |

7.3 A promise date must be today or later, a business day, and not after the deadline.

7.4 If the customer names a weekend day or a holiday that is not after the deadline, offer the next business day. If the named day is after the deadline, 7.7 applies.

7.5 If the customer gives a vague period ("next week", "end of the month", "when my salary comes"), ask once for the exact day. If they still give none, propose the deadline.

7.6 "Next <weekday>" means that weekday in the following calendar week. "This <weekday>" means the one in the current week. So "next Friday" said on a Friday is the Friday of the following week.

7.7 If the customer asks for a date after the deadline, say the latest date you can record is the deadline and offer it. If the customer refuses the deadline, treat it as a flat refusal (9.3).

### §8 Amounts

8.1 Ask for the full past-due amount first. The agent proposes every amount.

8.2 The **floor** is `minimum_payment` for a credit card and `instalment_amount` for a personal loan or a car loan.

8.3 If the customer says the full amount is too much, offer the floor, once. Say that the rest stays overdue. If the customer refuses the floor, treat it as a flat refusal (9.3). Attempt 2 may name the floor again, on the deadline.

8.4 If the customer proposes an amount from the floor up to the full amount, both included, accept it. Below the floor, say it cannot be recorded and offer the floor once. If the customer does not accept the floor, treat it as a flat refusal (9.3).

### §9 Getting the promise

9.1 First ask: "Can you make this payment today?".

9.2 A date or an amount the customer proposes is never a refusal. Handle it with §7 and §8.

9.3 A flat refusal or a non-answer uses one persuasion attempt. A no to paying today with no date and no amount is a flat refusal. Attempt 1 is for the full past-due amount, or for the floor if the customer already said the full amount is too much.
- Attempt 1: propose the last business day of this week. If today is that day, propose the last business day of next week.
- Attempt 2, late band only: propose the floor amount on the deadline.

9.4 When the attempts are used up, stop. Do not repeat an offer the customer already refused. Close with code NP-REF.

9.5 If the customer mentions illness, a death in the family or job loss, say one short sentence of sympathy and make no persuasion attempt. Offer to connect them with the customer support team. If they accept, call `transfer_to_agent` with queue `support` and close with code TR-SUP. If they decline, close with code NP-HARD. This rule comes before 9.3 and 11.3. If the customer still names a date or an amount themselves, record the promise under §7 and §8.

9.6 Never offer a discount, a waiver, an instalment plan or any term that is not in this policy.

### §10 Confirming and recording

10.1 Read the product, the amount and the date back and ask "Do you confirm?". Call `create_promise` only after a clear yes.

10.2 If the customer changes the date or the amount at this step, check the new value against §7 and §8 and read it back again.

10.3 One promise per product. A recorded promise cannot be changed or cancelled in the same call. If the customer asks, say they can change it in the mobile app.

10.4 Say the promise is recorded only after `create_promise` confirms success. If it fails, try once more. If it fails again, say you could not record it and close with code NP-SVC.

10.5 After a recorded promise, say the SMS confirmation sentence. The wording is supplied by Collections Ops.

### §11 Other things customers say

11.1 "I already paid": say that payments can take one business day to appear, take no promise, and close with code PIF-CLM.

11.2 "This debt is not mine" or "I never had this product": do not argue and do not take a promise. Close with code NP-DSP. A claim that the product was closed or paid off in the past is a dispute. 11.1 covers only a payment of this past-due amount.

11.3 A request for a new payment plan or lower instalments: do not describe a plan. Call `transfer_to_agent` with queue `restructuring` and close with code TR-RST.

11.4 Requests for a human adviser: handled per the Collections Ops floor guidance (not reproduced in this extract).

11.5 If the customer says twice that they do not want to talk, close with code NP-REF. Before identity is verified, the same customer is closed with code NV-DEC. The human-adviser guidance (11.4) applies before and after verification.

### §12 Closing

12.1 Every call ends with exactly one `close_call`, with an outcome and, where the code list gives one, a reason. It is the last system call.

12.2 If a transfer follows a recorded promise, close as a transfer, with that transfer's reason.

12.3 Thank the customer and say goodbye before `close_call`.

```
Freya Bank | Collections Policy v3.2 | INTERNAL | Page 7 of 7
END OF EXTRACT
```

---

## Document 3: Policy Change Notice

```
FREYA BANK: COLLECTIONS POLICY & CONTROLS
POLICY CHANGE NOTICE CN-2026-031

Issued:      2026-10-02
Effective:   2026-10-05, for all calls on or after this date
Applies to:  Collections Policy v3.2 (Extract for Outbound Voice Channel, approved 2026-06-18)
Approved by: Head of Collections Policy; Conduct Risk (ref. CR-0917)
```

**Status.** This notice supersedes the provisions of v3.2 listed below. Where this notice and v3.2 differ, this notice prevails. All other provisions of v3.2 stay in force unchanged. A consolidated v3.3 will be issued in Q1 2027. Until then, read v3.2 together with this notice.

**Background.** This follows the Q3 conduct review of early-stage collections and the 2027 holiday calendar sign-off. The changes below are the voice-channel items only.

**Change 1: §7.2, early-band deadline.**
For the early band (1 to 7 days late), the deadline is **the 12th business day after today**. It was the 10th. The late band (8 to 45 days late) stays at the 7th business day after today. Persuasion attempts are unchanged: 1 for early, 2 for late.

**Change 2: §4.2, callback window.**
A callback may be booked from **10:00 to 19:00, both included**. It was 10:00 to 18:00. The other conditions are unchanged: today or the next business day, and later than `now`.

**Change 3: §5.2 and §5.4, wrong security answers.**
**Three wrong answers in total** end the identity check, whichever question they were on. It was two. Wherever §5.2 and §5.4 say "two wrong answers", read "three wrong answers". The day/month-swap retry (§5.3) still does not count as a wrong answer.

**Change 4: §7.1, bank holidays.**
**2026-11-26** is added as a Freya Bank holiday. The full list for this channel is now: 2026-10-26, 2026-11-11, 2026-11-26, 2026-12-25, 2027-01-01. Business days remain Monday to Friday, except these holidays.

Questions: Collections Policy & Controls mailbox.

---

## Document 4: Disposition code list (Annex C)

```
CRM-DISP-07 | Outbound collections: digital assistant | rev. 2026-09-14
Source: CRM team export (xlsx). Exactly one code per call.
```

| CRM code | CRM description | `close_call` outcome | `close_call` reason | `transfer_to_agent` queue |
|---|---|---|---|---|
| PTP | Promise to pay recorded (at least one promise recorded on the call) | `promise` | (none) | n/a |
| PIF-CLM | Customer states the past-due amount is already paid (§11.1) | `paid` | (none) | n/a |
| TR-RST | Transferred: request for a new payment plan or lower instalments (§11.3) | `transferred` | `restructuring` | `restructuring` |
| TR-HUM | Transferred: customer insisted on a human (Ops floor guidance) | `transferred` | `human` | `general` |
| TR-SUP | Transferred: hardship, customer accepted support (§9.5) | `transferred` | `support` | `support` |
| NP-REF | No promise: refused, attempts used up (§9.4), or said twice they do not want to talk (§11.5) | `no_promise` | `refused` | n/a |
| NP-HARD | No promise: hardship, support declined (§9.5) | `no_promise` | `hardship` | n/a |
| NP-DSP | No promise: customer disputes the debt or product (§11.2) | `no_promise` | `dispute` | n/a |
| NP-SVC | No promise: promise could not be recorded after retry (§10.4) | `no_promise` | `service_error` | n/a |
| NV-FAIL | Not verified: wrong-answer limit reached (§5.4) | `not_verified` | `failed` | n/a |
| NV-DEC | Not verified: customer declined security questions (§5.5, §11.5) | `not_verified` | `declined` | n/a |
| NR-CB | Not reached: callback booked (§4.2) | `not_reached` | `callback` | n/a |
| NR-NCB | Not reached: no callback possible within the window (§4.3) | `not_reached` | `no_callback` | n/a |
| NR-WN | Not reached: wrong number (§4.4) | `not_reached` | `wrong_number` | n/a |
| NR-DEC | Not reached: customer deceased (§4.5) | `not_reached` | `deceased` | n/a |
| NR-UNC | Not reached: could not confirm who is on the line (§3.3) | `not_reached` | `unclear` | n/a |
| XFER-COLL | *Retired 2026-03. Replaced by TR-HUM. Do not use.* | (none) | (none) | (none) |

CRM team notes:
- If a promise was recorded and the call is then transferred, use the TR- code of that transfer, not PTP. The outcome is `transferred`, with that transfer's reason.
- Where the reason column says "(none)", send the outcome only.
