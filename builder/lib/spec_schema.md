# Spec dict schema (input of `calendar_rules` and `codegen`)

The spec-extraction LLM step reads the brief and emits ONE JSON object with these fields.
Every value comes from the brief. Missing optional fields fall back to the defaults shown.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `weekend_days` | list of weekday names or ints (Mon=0) | `["Saturday","Sunday"]` | Non-business weekdays |
| `holidays` | list of `"YYYY-MM-DD"` (or `{"date":..., "name":...}`) | `[]` | Bank holidays (never business days) |
| `week_start_day` | weekday name/int | `"Monday"` | Start of a calendar week ("this week", "next week") |
| `bands` | list of band objects (below) | required | Lateness bands, matched on `days_late` |
| `deadline_roll` | `previous_business_day` / `next_business_day` / `none` | `previous_business_day` | If a computed deadline is not a business day |
| `floor_field_by_product_type` | object `type -> field name in get_account product` | `{}` | Floor amount field, e.g. `credit_card -> minimum_payment` |
| `floor_field_default` | string | none | Floor field for types not listed |
| `floor_percent_by_product_type` / `floor_percent_default` | object / number | none | Alternative: floor = past_due x percent / 100 |
| `product_labels` | object `type -> spoken label`, `<field>` placeholders | type with `_` -> space | e.g. `"credit card ending <card_last4>"` (use `<...>`, never curly braces) |
| `weekday_convention` | `{"this": ..., "next": ...}` | `current_week` / `following_week` | `this`: `current_week` or `next_occurrence_inclusive`. `next`: `following_week` (weekday of the next calendar week), `next_occurrence` (first one after today), `occurrence_after_next` |
| `proposal_date_rule` | `last_business_day_of_week` / `next_business_day` / `today` | `last_business_day_of_week` | Date of persuasion attempt 1 (if today is that day -> same rule next week). Capped at the product deadline |
| `promise_business_day_only` | bool | `true` | Promise date must be a business day |
| `promise_min_offset_days` | int | `0` | Earliest promise = today + N (0 = today allowed) |
| `callback` | object (below) | none | Third-party callback window |
| `identity` | object (below) | none | Security questions |
| `sms_sentence` | string | `""` | Exact sentence to say after a recorded promise |
| `promise_retry_limit` | int | `1` | Extra `create_promise` tries after a failure |
| `promise_fail_instruction` | string | generic | What to do after the last failed try (e.g. close `no_promise`/`service_error`) |
| `products_var_names` | list of strings | `[]` | Extra variable names where the get_account products may be mapped |
| `date_table_days` | int | `25` | Length of the day table in `date_facts` |

## Band object

| Field | Type | Meaning |
|---|---|---|
| `name` | string | e.g. `early`, `late` |
| `min_days_late`, `max_days_late` | int or null | Inclusive range of `days_late` (null = open) |
| `deadline_unit` | `business_days` / `calendar_days` / `end_of_week` / `end_of_month` / `fixed_date` | How the deadline is counted from today |
| `deadline_count` | int | N for the unit (`business_days`: the N-th business day AFTER today; `end_of_week`/`end_of_month`: 0 = current, 1 = next) |
| `deadline_date` | `"YYYY-MM-DD"` | Only for `fixed_date` |
| `deadline_roll` | as top level | Per-band override |
| `attempts` | int | Persuasion attempts allowed in this band |
| `product_types` | list of types, optional | Band applies only to these product types (typed bands win over untyped) |

## `callback` object

| Field | Type | Default | Meaning |
|---|---|---|---|
| `allowed_days` | list of `today`, `next_business_day`, `tomorrow`, `next_<N>_business_days` | `["today","next_business_day"]` | Allowed callback dates |
| `start`, `end` | `"HH:MM"` | `00:00` / `23:59` | Window, both ends included |
| `must_be_after_now` | bool | `true` | Slot must be later than `now` |
| `business_days_only` | bool | `false` | `today` allowed only if it is a business day |

## `identity` object

| Field | Type | Meaning |
|---|---|---|
| `questions` | list of `{"field": <verify_identity field enum>, "type": "date"|"digits"|"text", "ask": <question text>}` in asking order | Security questions |
| `max_wrong_answers` | int | Total wrong answers before failure |
| `numeric_date_order` | `DMY` / `MDY` | How a digits-only date is read |
| `answer_param`, `field_param` | string | Body field names of `verify_identity` (default `answer`, `field`) |
| `fail_instruction`, `swap_instruction` | string | Text placed in `what_to_do_next` on failure / day-month swap |

## Outputs written into `vars` by `emit_date_facts_code` (all strings)

`today`, `today_spoken`, `n_products`, `attempt1_date`, `callback_dates`, `product_facts`, `date_facts`, and per product
`p<i>_id, p<i>_type, p<i>_label, p<i>_past_due, p<i>_days_late, p<i>_band, p<i>_deadline, p<i>_deadline_spoken,
p<i>_floor, p<i>_attempts, p<i>_attempt1_date` (i = 1..n, get_account order), plus unprefixed copies of product 1
(`product_id, label, past_due, days_late, band, deadline, deadline_spoken, floor, attempts`).

## Hooks (`codegen`)

| Function | Attach to | Effect |
|---|---|---|
| `emit_date_facts_code(spec)` | code node at start and after get_account | writes the vars above |
| `emit_get_account_post_hook(spec)` | get_account `post_process_code` | adds `label, band, floor_amount, persuasion_attempts, latest_promise_date(_spoken)` per product, refreshes vars |
| `emit_verify_identity_pre_hook(spec)` | verify_identity `pre_process_code` | date answers -> `YYYY-MM-DD`, digit answers -> digits |
| `emit_verify_identity_post_hook(spec)` | verify_identity `post_process_code` | `what_to_do_next`: verified / next question / wrong + left / swapped / unreadable / failed |
| `emit_create_promise_post_hook(spec)` | create_promise `post_process_code` | ok -> "IS recorded" + SMS sentence, sets `promise_recorded=yes`; fail -> retry once, then fail instruction |
| `emit_generic_post_hook(ok, fail)` | any other api_call | drops headers, adds `what_to_do_next` |
