# raw-brief-a: answer key (do NOT feed to the builder)

The source is `raw-brief-a.md`. Its effective rules are exactly Brief A's 47 rules (`briefs/brief-a.md`), so `public-test-set.json` (Brief A, all `now` = 2026-10-14T11:00) applies unchanged.

The precedence is stated in the email of 2026-10-06 09:12 and in the CN-2026-031 status paragraph. The change notice (issued 2026-10-02, effective 2026-10-05) supersedes Extract v3.2 where they differ.

## Overridden values (Extract v3.2 → Change Notice CN-2026-031)

| # | Extract location | Extract v3.2 value (outdated) | CN-2026-031 value (effective) | Brief A rule |
|---|---|---|---|---|
| 1 | §7.2 bands table, early row | deadline = 10th business day after today | deadline = **12th** business day after today. Late stays 7th, attempts stay 1/2 | rule 18 |
| 2 | §4.2 callback window | 10:00 to 18:00 (no "both included") | **10:00 to 19:00, both included**. Today or next business day, later than `now` | rule 6 |
| 3 | §5.2 and §5.4 wrong answers | two wrong answers in total end the check | **three** wrong answers in total, whichever question. The swap retry still doesn't count | rules 12, 14 |
| 4 | §7.1 holidays | 2026-10-26, 2026-11-11, 2026-12-25, 2027-01-01 (4 dates) | **2026-10-26, 2026-11-11, 2026-11-26, 2026-12-25, 2027-01-01** (adds 2026-11-26) | §7 preamble |

## A spec built from this material is wrong if it contains any of these

- an early-band deadline of "10th business day"
- a callback end time of 18:00
- an identity check that ends after "two wrong answers"
- a holiday list that is missing 2026-11-26

## Rules that appear only in the email thread (not in the extract), and must still be in the spec

| Rule (Brief A #) | Where |
|---|---|
| 24: never ask "how much can you pay?" | Priya, Q1 |
| "Brief A never uses `add_note`" | Priya, Q2 (and Marcus) |
| 38: verbatim "You will receive a text message confirming this promise." | Priya, Q3. The extract §10.5 only points to it |
| 43: "Is this a scam?" → verify via Freya Bank's customer service number, continue | Priya, Q5 |
| 42: human request → ask once if you can help, then `general` queue, `transferred`/`human`, before and after verification | Priya, Q5. The extract §11.4 only points to it |
| 44: say you don't have that information. No invented figures, dates or reasons | Hannah, point 2 |
| 11/13: DOB as `YYYY-MM-DD`, the service rejects unreadable dates, `hint: "day_month_swapped"` | Marcus |
| 37: success = `create_promise` returns `ok: true` | Marcus. The extract §10.4 says only "confirms success" |
| transfer queues `restructuring` / `general` / `support` | Marcus, and the Annex C queue column |

## Distractors (should NOT become rules)

- the XFER-COLL code (retired, "do not use")
- excluded full-policy sections 13 to 15 (Letters, Field visits, Agency placement)
- chatter: UAT cert rotation, recording-retention aside ("wrong thread"), steering committee, PO number, parking passes
