---
name: build-phone-agent
description: Build a Freya phone agent from a bank's brief, test it on the practice customers and fix what fails. Use when asked to build or improve a phone agent from a brief.
---

# Build a phone agent from a brief

Work in the folder you were started in; the bank's documents are in `input/`. Use only what the documents you were given say. Do not copy rules, values or names from another brief, from the practice briefs or from memory. Everything the agent knows about this bank comes from these documents.

The prompt gives you: the documents, a **slot**, a **mock base URL** (or none: then use the server URL in the tool API file) and a **hard stop time**. Have a saved, working workflow well before the hard stop. A saved agent that handles most cases beats a better one that was not saved in time.

## Steps

1. **Read every document.** The input may be one or more brief files, or a case folder with many kinds of documents. In a folder, read `BRIEF.md` first, then `README.md` (it says what each document is), then every other file, including images (Read shows them) and example conversations.
   - Precedence when documents disagree: a dated announcement or memo replaces the older text it names; an answer in a questions-and-answers document clarifies the brief; the service contract (tool API) decides field names and allowed values. Example conversations show tone and phrasing; they are not rules unless the brief agrees.
   - The tool API is the OpenAPI file or service contract among the inputs. If there are several, use the one the documents name for this case.
2. Read `docs/workflow-format.md` and `docs/tools-and-code.md`, and `examples/base-agent.json` as the JSON pattern (not as the answer).
3. **Write the spec first: `out/<slot>.spec.md`.** Short, numbered, with the source file of each item:
   - call variables and the language of the call
   - opening, who may be told what, third-party handling
   - identity: which questions, in which order, formats sent to the tool, retry and lock-out limits, hints the tool can return
   - every number: bands, limits, floors, deadlines, attempt counts, time windows, the calendar (business days, holidays) and how "today", "next <weekday>" etc. are resolved
   - every outcome and reason the close tool accepts, and exactly when each one applies (copy the table)
   - every sentence the brief says must be said, verbatim
   - every override you applied from an announcement or memo, and what it replaced
   - each tool: URL, required fields, enums, what a failure looks like and what the agent must do then
   Then go through the brief rule by rule and mark, for each rule, where the workflow will enforce it (route, code node, hook, prompt). A rule with no place is a bug.
4. Write the workflow to `out/<slot>.workflow.json`.
   - One step per stage of the call. Identity comes first. Tools that reveal or change the account exist only in steps after identity is verified.
   - Move to the next step on a tool result or a variable, not on what the customer says.
   - **Compute, do not ask the model to compute.** Dates (business days, deadlines, weekday resolution, holidays), amounts (floors, limits), counters (wrong answers, attempts per product) and the outcome/reason of the close call belong in code nodes or hooks that write variables. Prompts then quote those variables. Take holidays, bands and limits from the spec, never from another brief.
   - **Give dates as a lookup table, not as facts to reason over.** A list of facts ("deadline is X, holidays are Y") still leaves the model to pick the date, and it picks wrong. Have code write one line per calendar day from today to a few weeks past the latest deadline, each with its final answer, for example `2026-10-26 Monday: bank holiday -> offer 2026-10-27 Tuesday` or `2026-11-06 Friday: after the deadline -> say the latest date is 2026-10-23 and offer it`, plus ready lines for every relative phrase the brief defines ("this Friday = ...", "next Friday = ...", "end of this week = ...") in the call's language. The prompt says: find the day the customer named in the table and do exactly what its line says. With several products, one table per product or one column per product. Do the same for amounts when the brief has amount rules (full, floor, below floor -> what to say).
   - Take every tool field, URL path and allowed value from the tool API. Constrain model-filled fields with `enum`. Fill ids (customer, product) from variables or tool results, never from the model's memory.
   - **Failures come in several shapes**: `ok: false` in a 200 body, an HTTP 500 with or without a body, a timeout, an empty body. Give every `api_call` tool a `post_process_code` hook (see "Pre and post Python hooks" in tools-and-code.md) that turns all of them into one shape the model cannot misread: `result["data"] = {"ok": False, "error": "...", "what_to_do_next": "<what the brief says to do now, e.g. nothing was recorded, try once more / tell the customer>"}`, and on success adds a `what_to_do_next` line too. Count failures per tool in a variable so a route or the prompt knows whether this was the first or the second failure. Wrap every hook in `try/except Exception: pass`. If the practice customers include a tool failure, check in the transcript that the retry really happened.
   - **Every tool URL is the mock base URL plus the path from the tool API.** No other host. Before saving, grep the file for `http` and check.
   - Leave `agent_config` out. No `null` values.
5. Save it: `python3 -c "import freya,json,sys; print(json.dumps(freya.save_workflow(sys.argv[1], json.load(open(sys.argv[2])))))" <slot> out/<slot>.workflow.json`
   It prints `workflow_id` and `agent_id`. The same slot updates the same workflow. Save once early, as soon as the workflow is valid, and again after every fix.
6. Test it on the practice customers in `input/` (a JSON list of cases with `id`, `variables`, `script`, `expected`, `checks`).
   - On the kit's tool API: `python3 tools/run_cases.py <agent_id> --cases input/<cases file>`; add `--brief A` or `--brief B` to run only the cases of the brief you build.
   - On a mock given in the prompt: `FREYA_BANK_HOST=<mock base URL without /v1> python3 tools/run_cases.py <agent_id> --cases input/<cases file>`.
   - No cases file: skip the simulation and rely on the chat check below and on the rule-by-rule review.
   - Quick check without a simulation: one or two chat turns (`POST /api/v2/chat/message`, see `docs/api.md`) to see the opening sentence and the first question.
   A run takes 3 to 11 minutes. Run it in the foreground and wait for it to finish. Never start it in the background and never end your turn while a test is running: the builder stops when you stop. Do not start a test that cannot finish before the hard stop.
7. Read each FAIL line and its reason. Fix the cause in a way that would also be right for a different brief, save again, test again. At most three rounds. When a fix touches a shared part (a prompt, the date table, a route), rerun all cases, not only the failed ones: a fix for one case can break another.
   Never end on an untested save. If there is no time to test a change, save the last tested version again (`out/<slot>.tested.json`: copy the workflow there after every test run that scored at least as well as the one before) so the agent on Freya is one whose score you know.
   One green run is a hint, not proof: the same agent can fail the same customer next time. If everything passed and at least 12 minutes are left before the hard stop, run once more with `--style` set to one of `pieces`, `corrects`, `in_words`, `asks_back`, `talkative` and fix what breaks. Keep the last saved version that passed if a fix makes things worse.

## Several products per customer

If the account can hold more than one product, keep the per-product state in variables written by code, not in the model's memory: the ordered product list, each product's band, deadline, floor and attempts used, which product is being discussed now, and which got a promise, a note or nothing. Let code pick the next product and the outcome/reason of the close call from that state. The prompt only talks about the current product and quotes the values code computed.
8. Finish with one line: the `workflow_id`, the `agent_id` and how many customers passed in the last run. The builder script exports the workflow after you stop.

## Language

- The agent speaks the language of the brief and the call. If the brief, the example conversations or the call variables are in Turkish, every `on_enter` text, every prompt and every fixed sentence is in Turkish. Sentences the brief gives in quotes are said exactly as given.
- Customers say numbers and dates in words, in pieces, and correct themselves. The model converts what was said into the format the tool needs (for example `YYYY-MM-DD`, digits only) and the latest correction wins. In Turkish: amounts like "dört yüz elli lira", "bin iki yüz", "yüz yirmi beş buçuk"; dates like "yirmi üç Ekim", "ayın on beşi", "haftaya Cuma" (Friday of next week), "bu Cuma" (this week's Friday), "yarın", "öbür gün"; weekdays Pazartesi, Salı, Çarşamba, Perşembe, Cuma, Cumartesi, Pazar. Resolve weekday phrases in code from `now`, with the rule the brief gives.
- Read amounts and dates back in words a person understands in that language, not in ISO format.

## What real customers do

The customers talk like people. Make every step survive these without breaking a rule:
- give a number or a date in two parts, or say it in words
- correct themselves ("the 21st, sorry, the 20th"): use the corrected value
- talk about unrelated things, including dates that are not payment dates
- ask a question back before answering ("why do you need that?", "which account?"), ask whether this is a robot or a scam
- answer a question that was not asked yet, or several at once
- someone else answers the phone
A question back is not a refusal and not an answer. Answer it in one sentence and ask again.

## Rules

- Never edit the agent on the platform by hand. Change the file and save it.
- When a tool call fails, the agent must say so. It must never tell the customer something is recorded when it is not.
- A customer that passes once can fail the next time. Prefer rules in routes and code over rules in prompts.
- One `close_call` per call, as the last tool call, with the outcome and reason the brief requires.
