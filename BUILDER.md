# Our builder: how to run it

One command per brief:

```bash
source env.sh                         # FREYA_API_KEY, FREYA_API_URL, FREYA_BANK_TEAM_KEY (+ a Claude login or ANTHROPIC_API_KEY)
pip install claude-agent-sdk
python3 builder/build.py {brief_path} {tool_api_path} 2>&1 | tee traces/<slot>.console.log
```

- `{brief_path}`: one Markdown brief (clean specification or raw bank material). Several briefs may be given before the tool API file when one builds on another (`briefs/brief-a.md briefs/brief-b.md tools/openapi.json`).
- `{tool_api_path}`: the brief's tool API file (OpenAPI JSON).
- Run time: at most 27 minutes (`BUILDER_BUDGET_S`), including self-tests. Builder model: `BUILDER_MODEL` (default `claude-opus-5-5`).

What happens:

1. `out/` starts empty (earlier runs move to `out_prev/`), so a run depends only on this commit and the brief.
2. Claude (Claude Agent SDK) follows the skill `.claude/skills/build-phone-agent-pro/SKILL.md`: reads the whole brief and tool API, writes `out/<slot>.spec.json` (every rule with an id; memos in raw material override older rules), writes a generator `out/gen_<slot>.py` using `builder/lib/wfkit.py` (valid workflow shapes) and `builder/lib/codegen.py` (deterministic date/amount/identity code and hooks), produces `out/<slot>.workflow.json` and `out/<slot>.coverage.md` (rule → mechanism).
3. `builder/lint.py` checks the workflow statically (dropped fields, dead ends, tool fields/enums against the tool API, close_call once, code without `{{ }}`, unset prompt variables, routing on enum values).
4. `freya.save_workflow(<slot>, ...)` creates the workflow once and updates it in place afterwards (published).
5. Self-tests: `builder/smoke.py <workflow_id>` (chat turns: opening must not leak, call must start); on the kit's practice briefs also `tools/run_cases.py`. At most two fix rounds.
6. `build.py` exports the workflow with `freya.export_workflow` to `submission/<slot>.workflow.json` and writes the trace `traces/<slot>-<time>.log` (start/end, every model call with model and one-line purpose, workflow/agent ids, step and tool counts, self-test results) plus the full message log `traces/<slot>-<time>.jsonl`.

Practice results and edge cases: `results/` (local), `evals/edge_cases.json` + `evals/run_edge.py` (42 extra cases on the practice bank data), `evals/briefs/raw-brief-a.md` (Brief A rewritten as raw bank material with an overriding memo).
