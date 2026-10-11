"""Builder: reads a bank's brief and its tool API file, creates the phone agent on Freya, tests it, exports it.

    python3 builder/build.py <brief.md> [<more briefs.md> ...] <tool_api.json>

One command, no manual step. Claude (via the Claude Agent SDK) works with the skill
`.claude/skills/build-phone-agent-pro`, the deterministic helpers in `builder/lib/`, the linter `builder/lint.py`
and the self-tests (`tools/run_cases.py` when the brief has practice customers, `builder/smoke.py` otherwise).

Outputs:
  out/<slot>.workflow.json         the workflow the builder wrote
  submission/<slot>.workflow.json  the workflow as stored on Freya (freya.export_workflow)
  traces/<slot>-<time>.log         plain-text trace: times, every model call with a one-line purpose,
                                   what was created on Freya, self-tests and results
  traces/<slot>-<time>.jsonl       every SDK message of the run

Needs FREYA_API_KEY, FREYA_BANK_TEAM_KEY and a Claude login or ANTHROPIC_API_KEY.
"""
import asyncio, dataclasses, json, os, pathlib, re, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import freya  # noqa: E402

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock,  # noqa: E402
                              ToolResultBlock, ToolUseBlock, UserMessage, query)

MODEL = os.environ.get("BUILDER_MODEL", "claude-opus-5-5")
BUDGET_S = int(os.environ.get("BUILDER_BUDGET_S", str(27 * 60)))   # the rules allow 30 minutes per brief


def practice_brief(briefs):
    """'A' or 'B' when the kit has practice customers for this brief, else None. Decided from file names only."""
    names = [pathlib.Path(b).stem.lower() for b in briefs]
    if any(n.endswith("brief-b") for n in names):
        return "B"
    if any(n.endswith("brief-a") for n in names):
        return "A"
    return None


class Trace:
    def __init__(self, slot):
        stamp = time.strftime("%Y%m%d-%H%M%S")
        (ROOT / "traces").mkdir(exist_ok=True)
        self.log = open(ROOT / "traces" / f"{slot}-{stamp}.log", "w", encoding="utf-8")
        self.jsonl = open(ROOT / "traces" / f"{slot}-{stamp}.jsonl", "w", encoding="utf-8")
        self.calls = 0
        self.tests = []

    def line(self, s):
        self.log.write(s + "\n")
        self.log.flush()
        print(s, flush=True)

    def message(self, m):
        self.jsonl.write(json.dumps({"t": time.strftime("%H:%M:%S"), "type": type(m).__name__, **dataclasses.asdict(m)}, default=str) + "\n")
        self.jsonl.flush()
        if isinstance(m, AssistantMessage):
            self.calls += 1
            purpose = ""
            for b in m.content:
                if isinstance(b, TextBlock) and b.text.strip():
                    purpose = b.text.strip().splitlines()[0][:160]
                    break
                if isinstance(b, ToolUseBlock):
                    arg = b.input.get("command") or b.input.get("file_path") or b.input.get("pattern") or ""
                    purpose = f"{b.name}: {str(arg)[:140]}"
                    break
            self.line(f"[{time.strftime('%H:%M:%S')}] model call {self.calls} ({getattr(m, 'model', MODEL) or MODEL}): {purpose}")
        elif isinstance(m, UserMessage) and isinstance(m.content, list):
            for b in m.content:
                if isinstance(b, ToolResultBlock):
                    text = b.content if isinstance(b.content, str) else json.dumps(b.content, default=str)
                    for ln in text.splitlines():
                        ln = ln.strip()
                        if re.match(r"^\d+ / \d+ passed", ln) or ln.startswith("SMOKE ") or re.match(r"^lint: \d+ errors", ln) \
                                or re.match(r"^(PASS|FAIL) (PUB|EDGE)-", ln):
                            self.tests.append(ln.strip())
                            self.line(f"    self-test: {ln.strip()[:200]}")


def build_prompt(briefs, api, slot, letter):
    test = (f"This brief has practice customers: test with `python3 tools/run_cases.py <agent_id> --brief {letter}`."
            if letter else "This brief has NO practice customers. Self-test with `python3 builder/lint.py` and `python3 builder/smoke.py <workflow_id>` only.")
    return (f"Use the build-phone-agent-pro skill to build the phone agent.\n"
            f"Brief file(s), read every line: {', '.join(briefs)}\n"
            f"Tool API file: {api}\n"
            f"Slot (use it for out/<slot>.workflow.json and freya.save_workflow): {slot}\n"
            f"{test}\n"
            f"Time budget: {BUDGET_S // 60} minutes in total, including tests. Save a valid workflow early and improve it in place.")


async def run(briefs, api, slot, trace):
    letter = practice_brief(briefs)
    options = ClaudeAgentOptions(
        cwd=ROOT, model=MODEL, skills=["build-phone-agent-pro"], setting_sources=["project"],
        allowed_tools=["Read", "Write", "Edit", "Glob", "Grep", "Bash"], permission_mode="dontAsk", max_turns=200,
        env={"BASH_DEFAULT_TIMEOUT_MS": "900000", "BASH_MAX_TIMEOUT_MS": "1200000", "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1",
             "PYTHONIOENCODING": "utf-8"},
    )
    async for m in query(prompt=build_prompt(briefs, api, slot, letter), options=options):
        trace.message(m)
        if isinstance(m, ResultMessage):
            trace.line(f"builder agent finished: {m.num_turns} turns, {m.duration_ms / 1000:.0f} s, ${m.total_cost_usd or 0:.2f}")


def main():
    args = sys.argv[1:]
    if len(args) < 2 or not args[-1].endswith(".json"):
        sys.exit(__doc__)
    briefs, api = args[:-1], args[-1]
    slot = pathlib.Path(briefs[-1]).stem
    t0 = time.time()
    # A run starts from a clean out/ so it depends only on the committed code and the given brief,
    # exactly like a rebuild from a fresh clone. Earlier runs are kept in out_prev/ (not committed).
    out = ROOT / "out"
    if out.exists():
        import shutil
        prev = ROOT / "out_prev" / time.strftime("%Y%m%d-%H%M%S")
        prev.parent.mkdir(exist_ok=True)
        shutil.move(str(out), str(prev))
    out.mkdir()
    trace = Trace(slot)
    trace.line(f"start: {time.strftime('%Y-%m-%dT%H:%M:%S%z')}  builder model: {MODEL}  briefs: {briefs}  tool api: {api}  slot: {slot}")
    try:
        asyncio.run(asyncio.wait_for(run(briefs, api, slot, trace), timeout=BUDGET_S))
    except asyncio.TimeoutError:
        trace.line(f"time budget of {BUDGET_S} s reached: stopping the builder agent, keeping the last saved workflow")
    except Exception as e:  # keep whatever was saved; the trace records the failure
        trace.line(f"builder agent error: {type(e).__name__}: {e}")

    state_f = ROOT / ".freya-agents.json"
    state = json.loads(state_f.read_text()) if state_f.exists() else {}
    if slot not in state:
        trace.line("no workflow was saved for this slot")
    else:
        ids = state[slot]
        (ROOT / "submission").mkdir(exist_ok=True)
        path = freya.export_workflow(ids["workflow_id"], str(ROOT / "submission" / f"{slot}.workflow.json"))
        wf = json.loads(pathlib.Path(path).read_text())["workflow"]
        n_nodes = len(wf.get("nodes", {})) + len(wf.get("global_nodes", {}) or {})
        n_tools = sum(len(n.get("tools", []) or []) + len(n.get("pre_actions", []) or []) for n in wf.get("nodes", {}).values()) + len(wf.get("tools", []) or [])
        trace.line(f"created on Freya: workflow_id={ids['workflow_id']} agent_id={ids['agent_id']} version={ids.get('version')} steps={n_nodes} tools={n_tools}")
        trace.line(f"exported: {path}")
    trace.line("self-tests: " + (" | ".join(trace.tests[-6:]) if trace.tests else "none recorded"))
    trace.line(f"end: {time.strftime('%Y-%m-%dT%H:%M:%S%z')}  build time: {time.time() - t0:.0f} s  model calls: {trace.calls}")


if __name__ == "__main__":
    main()
