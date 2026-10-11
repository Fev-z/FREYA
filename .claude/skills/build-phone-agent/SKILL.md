---
name: build-phone-agent
description: Build a Freya phone agent from a bank's brief, test it on the practice customers and fix what fails. Use when asked to build or improve a phone agent from a brief.
---

# Build a phone agent from a brief

Work from the kit folder. Use only what the documents you were given say. Do not copy rules, values or names from another brief, from the practice briefs or from memory. Everything the agent knows about this bank comes from these documents.

The prompt gives you: the documents, a **slot**, a **mock base URL** (or none: then use the server URL in the tool API file) and a **hard stop time**. Have a saved, working workflow well before the hard stop. A saved agent that handles most cases beats a better one that was not saved in time.

## Steps

1. **Read every document.** The input may be one or more brief files, or a case folder with many kinds of documents. In a folder, read `BRIEF.md` first, then `README.md` (it says what each document is), then every other file, including images (Read shows them) and example conversations.
   - Precedence when documents disagree: a dated announcement or memo replaces the older text it names; an answer in a questions-and-answers document clarifies the brief; the service contract (tool API) decides field names and allowed values. Example conversations show tone and phrasing; they are not rules unless the brief agrees.
   - The tool API may be `tools/openapi.json` or a service contract inside the folder. Use the one the documents name for this case.
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
   - Take every tool field, URL path and allowed value from the tool API. Constrain model-filled fields with `enum`. Fill ids (customer, product) from variables or tool results, never from the model's memory.
   - **Every tool URL is the mock base URL plus the path from the tool API.** No other host. Before saving, grep the file for `http` and check.
   - Leave `agent_config` out. No `null` values.
5. Save it: `python3 -c "import freya,json,sys; print(json.dumps(freya.save_workflow(sys.argv[1], json.load(open(sys.argv[2])))))" <slot> out/<slot>.workflow.json`
   It prints `workflow_id` and `agent_id`. The same slot updates the same workflow. Save once early, as soon as the workflow is valid, and again after every fix.
6. Test it.
   - Practice briefs on the kit's tool API: `python3 tools/run_cases.py <agent_id> --brief A` (or `--brief B`).
   - Your own mock: if it has practice routes and there is a cases file in the case folder or `mock/cases.json`, run `FREYA_BANK_HOST=<mock base without /v1> python3 tools/run_cases.py <agent_id> --cases <file>`.
   - Quick check without a simulation: one or two chat turns (`POST /api/v2/chat/message`, see `docs/api.md`) to see the opening sentence and the first question.
   A run takes 3 to 11 minutes. Run it in the foreground and wait for it to finish. Never start it in the background and never end your turn while a test is running: the builder stops when you stop. Do not start a test that cannot finish before the hard stop.
7. Read each FAIL line and its reason. Fix the cause in a way that would also be right for a different brief, save again, test again. At most three rounds.
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
