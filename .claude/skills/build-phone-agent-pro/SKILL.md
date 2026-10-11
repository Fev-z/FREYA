---
name: build-phone-agent-pro
description: Build a reliable Freya phone agent (workflow) from a bank's collections brief and its tool API file, lint it, save it, self-test it and fix it within the time budget. Use whenever asked to build or improve a phone agent from a brief.
---

# Build a phone agent from a brief

You are the builder. You read a bank's brief (a clean specification, or raw bank material: mails, policy extracts, memos that change them, code lists) and the tool API file, and you produce a Freya **workflow** that a weak model runs on the phone. It is scored on simulated customers, three runs each: a customer counts only if all three runs are perfect. **Reliability beats elegance. Put every rule you can into code, routes and fixed lines, not into prompt prose.**

Work from the repository root. Never copy a rule, value, name or date from another brief or from this skill into the agent: everything comes from the brief you were given and its tool API file.

## Time plan (hard limit: the budget in your prompt)

1. **Read** (≈4 min): every line of the brief file(s), the tool API file, `docs/workflow-format.md`, `docs/tools-and-code.md`. Skim `examples/base-agent.json` for valid JSON shapes only.
2. **Spec** (≈5 min): write `out/<slot>.spec.json` (schema: `builder/lib/spec_schema.md`). Every rule gets an id and its verbatim text.
3. **Workflow** (≈8 min): write `out/<slot>.workflow.json` following the blueprint below. Generate date/amount code with `builder/lib` (see "Deterministic layer").
4. **Lint**: `python3 builder/lint.py out/<slot>.workflow.json <tool_api>` until it reports 0 errors. Fix warnings that matter.
5. **Save**: `python3 -c "import freya,json,sys; print(json.dumps(freya.save_workflow(sys.argv[1], json.load(open(sys.argv[2])))))" <slot> out/<slot>.workflow.json`. Save a first valid version EARLY; later saves update it in place.
6. **Self-test**: `python3 builder/smoke.py <workflow_id>` always. If your prompt says the brief has practice customers, also `python3 tools/run_cases.py <agent_id> --brief <A|B>` in the FOREGROUND and wait for it (3-11 min). Read every FAIL reason. Fix the workflow file, lint, save, test again. At most two fix rounds; stop with time to spare.
7. **Finish** with one line: workflow_id, agent_id, last test result.

Never end your turn while a test is running. Never edit the agent on the platform by hand. Never weaken a test.

## Step 2: the spec, done right

- Read the whole brief. Most failures come from one skipped rule.
- **Raw material**: identify every document (mail, policy extract, memo, code list). A memo or a later dated document that changes a rule replaces it; note which rule it overrides. A code list defines the exact outcome/reason/queue values to send. Ignore greetings, signatures and chatter. If two documents conflict and none says which wins, take the most recent one and list the conflict in `ambiguities`.
- Extract into the spec: call variables (names, formats, `now`), opening sentence(s) and forbidden words before identity, who may be told what (third parties), identity questions in order + answer formats + retry/limit rules + special hints, the calendar (business days, holidays), deadline rule and bands, persuasion attempts, amount floors per product type, date rules (vague dates, weekday expressions, weekend/holiday handling), callback window, outcome table (outcome, reason, when), fixed sentences that must be said verbatim, special situations (paid, dispute, hardship, restructuring, human, scam, robot, deceased, wrong number, refusal), multi-product rules (order, notes, read-back, per-product deadlines).
- Take every tool field name and allowed value from the tool API file. Fields and enums can differ from what you expect.
- Write `out/<slot>.coverage.md`: one line per rule id saying where it is enforced (node + mechanism: code, route, hook, fixed line, prompt). A rule with no line is a bug.

## Step 3: blueprint of a collections call

Default graph. Adapt it to the brief (other identity questions, other outcomes, more steps), but keep the principles.

```
setup (code, passthrough, initial)      compute date facts from {{now}} + spec constants into vars (strings)
  -> opening (conversation)             fixed opening line (on_enter tts) + "Am I speaking with ...?"
       routes on extracted enum `party`: confirmed | third_party | wrong_number | deceased | declined | unclear
  -> third_party (conversation)         say nothing about the reason; ask when the customer can be reached;
                                        schedule_callback tool; routes to closing on its result / on refusal
  -> identity (conversation)            verify_identity tool, one question at a time, in the brief's order
       routes on tool result variables: all verified -> load_account; no attempts left -> close (failed)
       route on extracted enum for declining -> close (declined)
  -> load_account (api_request, passthrough)   get_account in pre_actions, node-level response_mapping data.products
  -> account_facts (code, passthrough)  per product: band, deadline, floor, attempts, product name in words,
                                        allowed dates; writes `account_facts` and `date_facts` text for prompts
  -> negotiate (conversation)           state the debt, ask for payment today, dates/amounts, persuasion,
                                        special situations, read-back + confirmation, create_promise / add_note /
                                        transfer_to_agent tools; routes to closing on an extracted `call_result` enum
  -> closing nodes                      say the required closing sentence, then end_call nodes
close_call: workflow-level lifecycle tool (alwaysRunsAt end_of_call) -> exactly one, always last
```

Rules that make it reliable (each one comes from the platform docs or from failed practice runs):

- **Routing**: leave a step on a **tool result variable** (`<tool>_response.data.<field>`, test `"true"` and `"True"`) or on an **extracted enum** with `equals`. Use `matches_intent` only as a last resort. Put deterministic conditions first; end with a self-transition `always`. Every path must reach an end.
- **Opening**: the first sentence and the identity question are a fixed `on_enter` `tts` line built from the brief's exact wording with `{{title}}`/`{{last_name}}` etc. No reason for the call before identity passes. Answer "are you a robot/AI?" and "is this a scam?" per the brief, then repeat the pending question (it counts per the brief's rule).
- **Identity**: the dialogue model calls `verify_identity` once per answer, with the `field` enum from the tool API. Convert spoken dates to the API format (for example `YYYY-MM-DD`) in the tool description. Wait for a complete answer: a customer may give a number in two parts ("44..." then "71"); never send a partial value. If the customer corrects themselves, use the corrected value. Add a **post-hook** to verify_identity that writes `what_to_do_next` into `result['data']` from `verified`, `all_verified`, `wrong_answers_left`, `hint` (for example: "Correct. Ask the next question: ..."; "Wrong. N attempts left. Ask the same question again."; "Day and month look swapped: ask for the month as a word; this does not count as wrong"; "No attempts left: do not state the debt; say <brief's sentence>; then end the call").
- **Account**: `get_account` runs as engine-run `pre_actions` (never skipped), then a code node computes all numbers. The model never computes dates or floors: it reads `{{account_facts}}` and `{{date_facts}}` in its task message.
- **Negotiation prompt** (task_message): numbered steps in the brief's order, the persuasion ladder per band with exact proposals (already computed in the facts), the date rules (vague period -> ask once for the exact day; weekend/holiday -> offer the next allowed day from the facts table; after the deadline -> offer the deadline), the amount rules (ask for the full amount first; never ask "how much can you pay"; floor rules), special situations with the exact outcome they lead to, read-back + "Do you confirm?" + call create_promise only after a clear yes, one promise per product, never offer anything not in the brief.
- **Honesty**: `create_promise` (and every write tool) gets `maxRetries: 0` and a post-hook: on `ok: true` -> "Recorded. Now say exactly: <brief's confirmation sentence>."; on failure -> "NOT recorded. Do not say it was recorded. Try once more with the same values" and on the second failure "Tell the customer you could not record it" (+ the brief's outcome for it). Say in the prompt: after every tool result, speak to the customer or call the next tool; never end a turn with nothing.
- **Multi-product** (if the brief has it): state every late product first, ask about paying all today once, then go product by product in `get_account` order with per-product attempts and deadlines; read all promises back together, one confirmation, then one create_promise per product; add_note for each product without a promise with the right reason; no notes on a transfer. Give the model a per-product checklist in the facts text.
- **Closing**: `close_call` is a workflow-level tool with `config.alwaysRunsAt: ["end_of_call"]`, body `outcome`/`reason` with the exact enums of the tool API and descriptions copied from the brief's outcome table (when each applies), and a `pre_process_code` hook that drops `reason` for outcomes that have none. Where a path decides the outcome deterministically (failed identity, declined, wrong number, deceased, callback, transfer), set `close_outcome`/`close_reason` variables in a code node or hook on that path and use `"default": "{{close_outcome}}"` so no model guesses. Say the brief's goodbye in the last conversation turn or as the end_call `spoken_message`.
- **System prompt**: identity of the assistant, English, one or two short sentences per turn, one question at a time, never invent figures/dates/reasons, call tools when a rule says so, speak after every tool result, numbers and dates may arrive in words or in pieces: wait for the complete value and confirm it.
- **test_variables**: plausible values for every call variable of the brief (for the chat smoke test), including `now`.
- Write `task_message` as instructions for that step only. Never mention node names or routing in prompts. In nodes without tools, say no tool call is allowed.

## Situations a hidden brief or customer can bring (map each to the brief's rule, or to a safe default)

Check your spec for each line. If the brief has a rule, follow it exactly. If it has none, use the safe default and note it in `ambiguities`.

- Identity answers of other kinds: postcode (keep letters, spaces and leading zeros as the customer says them, normalise case), year of birth (four digits; "eighty-eight" is 1988 only if the brief allows two-digit years, else ask for all four), company number or founded year (digits as strings, keep leading zeros). Convert words to digits. Never send a partial value. Never read identity data back to the caller and never ask for card numbers, PINs or passwords.
- Business customers: the person on the line may be staff or a representative. Who may answer and what may be disclosed comes from the brief; if it says nothing, treat anyone who is not the named contact as a third party.
- Phone handed to someone else mid-call, or the customer says "I'm his wife" after confirming: treat the new speaker as a third party for anything not yet disclosed.
- "Stop calling me", a lawyer or a complaint: no persuasion; the brief's refusal or human-transfer rule decides the outcome.
- "I'm paying right now / I will pay in the app today": that is a promise for today if the brief records promises for today; "I already paid" is the paid rule. Do not mix them.
- A verified customer asking for a callback instead of talking now: follow the brief's callback/refusal rule; never schedule outside its window.
- Partial amount offers: apply the floor rules exactly; amounts and dates come back from the customer as words, pieces or corrections.
- Questions back ("why do you need that?", "which account?"): answer per the brief without disclosing anything before identity, then repeat the pending question.
- Off-topic talk: one short sentence, then return to the pending question. A date mentioned as small talk is never a payment date unless the customer offers it for payment.

## Deterministic layer (`builder/lib`)

Read `builder/lib/spec_schema.md`. Use `builder/lib/codegen.py` to emit the code for the `setup`/`account_facts` code nodes and the post-hooks from your spec, for example:

```bash
python3 -c "import sys,json; sys.path.insert(0,'builder'); from lib import codegen; spec=json.load(open('out/<slot>.spec.json')); print(codegen.__doc__)"
```

Inspect the emitted code before you paste it. It must not contain `{{` or `}}`, must never raise, and must write strings into `vars`. If the brief's date or amount rules differ from what the library supports, write the code yourself following the same rules, and test it locally with `python3` on a fake `vars` dict before saving.

## Checklist before every save

- lint: 0 errors.
- Every rule id in `out/<slot>.coverage.md` has a mechanism.
- Tool names, fields and enums exactly as in the tool API file; `customer_id` baked as `{{customer_id}}`; URLs on the tool API host only.
- Exactly one close_call (lifecycle), write tools `maxRetries: 0`, post-hooks on verify_identity and create_promise.
- Fixed sentences from the brief appear verbatim in `tts` lines, `spoken_message` or hook instructions.
