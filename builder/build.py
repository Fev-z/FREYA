"""The builder: one command, the bank's documents in, a phone agent on Freya out.

    python3 builder/build.py <case_folder_or_brief_files...> [--mock https://your-mock.workers.dev] [--slot name]

    python3 builder/build.py briefs/brief-a.md briefs/brief-b.md          # practice, kit mock
    python3 builder/build.py FreyaBank-Ekstre-Borc/ https://x.workers.dev  # final

Claude runs through the Claude Agent SDK with the skill in .claude/skills/build-phone-agent. It reads every
document, writes the workflow, saves it on Freya, tests it and fixes it. When it stops (or the time budget runs
out) this script exports the saved workflow to submission/<slot>.workflow.json and checks every tool URL.

Trace: traces/<start>-<slot>.log (plain text, what the reviewers read) and a .jsonl with every message.
Needs FREYA_API_KEY and FREYA_BANK_TEAM_KEY (env.sh) and a Claude login or ANTHROPIC_API_KEY.
"""
import argparse, asyncio, dataclasses, json, os, pathlib, re, sys, time

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock, ToolResultBlock,
                              ToolUseBlock, UserMessage, query)

KIT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT))
import freya

SKILL = os.environ.get("BUILDER_SKILL", "build-phone-agent")
MODEL = os.environ.get("BUILDER_MODEL", "claude-opus-5-5")
BUDGET_MIN = float(os.environ.get("BUILD_MINUTES", "28"))     # README: one builder run takes 30 minutes at most
DOC_EXT = {".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".tsv", ".pdf", ".png", ".jpg", ".jpeg", ".html", ".xml", ".docx", ".xlsx"}


def now(): return time.strftime("%Y-%m-%dT%H:%M:%S%z")


# The trace is committed: never let a key into it.
SECRETS = [v for k in ("FREYA_API_KEY", "FREYA_BANK_TEAM_KEY", "ANTHROPIC_API_KEY") if len(v := os.environ.get(k, "")) >= 8]
def scrub(s):
    for v in SECRETS: s = s.replace(v, "***")
    return s


def collect_inputs(paths):
    """Every document the builder is given: files as they are, folders walked recursively."""
    files = []
    for p in map(pathlib.Path, paths):
        if p.is_dir():
            files += sorted(f for f in p.rglob("*") if f.is_file() and not f.name.startswith(".") and (f.suffix.lower() in DOC_EXT or not f.suffix))
        elif p.is_file():
            files.append(p)
        else:
            sys.exit(f"not found: {p}")
    return [f.resolve() for f in files]


# What a run may see: the platform docs, the Freya client, the test tools, the skill, the base example.
# Not the practice briefs, not earlier workflows or generators: a final agent must come from the final documents only.
KIT_FILES = ["freya.py", "docs/workflow-format.md", "docs/tools-and-code.md", "docs/api.md", "tools/run_cases.py", "tools/score.py",
             "examples/base-agent.json", ".claude/skills"]


def make_workspace(slot, files, stamp):
    import shutil
    ws = KIT / "runs" / f"{stamp}-{slot}"
    for rel in KIT_FILES:
        src, dst = KIT / rel, ws / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst) if src.is_dir() else shutil.copy2(src, dst)
    root = pathlib.Path(os.path.commonpath([f.parent for f in files])) if files else KIT
    for f in files:                                           # inputs keep their folder layout under input/
        dst = ws / "input" / f.relative_to(root)
        dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(f, dst)
    for keep in (".freya-agents.json", ".personas.json"):     # slot -> workflow map (same slot updates in place), test customers made before
        if (KIT / keep).exists(): shutil.copy2(KIT / keep, ws / keep)
    (ws / "out").mkdir(exist_ok=True)
    return ws, sorted(p for p in (ws / "input").rglob("*") if p.is_file())


def merge_state_back(ws, slot):
    src = ws / ".freya-agents.json"
    if not src.exists(): return
    got = json.loads(src.read_text()).get(slot)
    if not got: return
    dst = KIT / ".freya-agents.json"
    state = json.loads(dst.read_text()) if dst.exists() else {}
    state[slot] = got; dst.write_text(json.dumps(state, indent=1))


def slot_for(paths):
    p = pathlib.Path(paths[0])
    name = p.name if p.is_dir() else "+".join(pathlib.Path(x).stem for x in paths)
    return re.sub(r"[^A-Za-z0-9_.+-]", "-", name)


class Trace:
    """Plain-text trace: start and end, each model call (model + one-line purpose), what was created on Freya, tests."""

    def __init__(self, slot, stamp):
        (KIT / "traces").mkdir(exist_ok=True)
        self.log = (KIT / "traces" / f"{stamp}-{slot}.log").open("w")
        self.jsonl = (KIT / "traces" / f"{stamp}-{slot}.jsonl").open("w")
        self.path = self.log.name
        self.model_calls = 0

    def line(self, kind, text):
        msg = scrub(f"{now()}  {kind:<8} {text}")
        print(msg, flush=True)
        self.log.write(msg + "\n"); self.log.flush()

    def raw(self, message):
        self.jsonl.write(scrub(json.dumps({"at": now(), "type": type(message).__name__, **dataclasses.asdict(message)}, default=str)) + "\n")
        self.jsonl.flush()


def one_line(s, n=160):
    return " ".join(str(s).split())[:n]


def tool_result_text(block):
    c = block.content
    if isinstance(c, list): c = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
    return c or ""


async def run_claude(trace, prompt, options):
    pending = {}                                              # tool_use_id -> tool name, to label results
    async for message in query(prompt=prompt, options=options):
        trace.raw(message)
        if isinstance(message, AssistantMessage):
            trace.model_calls += 1
            texts = [b.text for b in message.content if isinstance(b, TextBlock) and b.text.strip()]
            uses = [b for b in message.content if isinstance(b, ToolUseBlock)]
            purpose = texts[0] if texts else ", ".join(f"{u.name}: {u.input.get('description') or one_line(u.input, 80)}" for u in uses)
            trace.line("MODEL", f"{getattr(message, 'model', MODEL)} | {one_line(purpose)}")
            for u in uses:
                pending[u.id] = u.name
                cmd = u.input.get("command", "")
                if "run_cases.py" in cmd: trace.line("TEST", "started: " + one_line(cmd, 200))
                elif "save_workflow" in cmd: trace.line("FREYA", "saving workflow: " + one_line(cmd, 200))
        elif isinstance(message, UserMessage) and isinstance(message.content, list):
            for b in message.content:
                if not isinstance(b, ToolResultBlock): continue
                out = tool_result_text(b)
                for m in re.finditer(r'\{[^{}]*"workflow_id"[^{}]*\}', out): trace.line("FREYA", "saved: " + m.group(0))
                for m in re.finditer(r"^(PASS|FAIL) .*$|^\d+ / \d+ passed.*$", out, re.M): trace.line("TEST", one_line(m.group(0), 240))
        elif isinstance(message, ResultMessage):
            trace.line("CLAUDE", f"done: {message.num_turns} turns, {message.duration_ms / 1000:.0f} s, ${message.total_cost_usd or 0:.2f}")


def check_and_export(trace, slot, mock):
    """Export what is saved on Freya under this slot. That file is what gets submitted and scored."""
    state_file = KIT / ".freya-agents.json"
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
    if slot not in state:
        trace.line("ERROR", f"no workflow saved under slot '{slot}' in .freya-agents.json")
        return None
    wid, aid = state[slot]["workflow_id"], state[slot]["agent_id"]
    (KIT / "submission").mkdir(exist_ok=True)
    path = KIT / "submission" / f"{slot}.workflow.json"
    freya.export_workflow(wid, str(path))
    wf = json.loads(path.read_text())["workflow"]
    nodes = wf.get("nodes", {})
    tools = [t for n in nodes.values() for t in (n.get("tools") or []) + (n.get("pre_actions") or [])] + (wf.get("tools") or [])
    names = sorted({t.get("function", {}).get("name", "?") for t in tools})
    trace.line("FREYA", f"workflow_id {wid}, agent_id {aid}, {len(nodes)} steps, {len(tools)} tool entries ({', '.join(names)})")
    trace.line("EXPORT", str(path))
    urls = sorted(set(re.findall(r'https?://[^"\s{}]+', json.dumps(wf))))
    if mock:
        bad = [u for u in urls if not u.startswith(mock.rstrip("/"))]
        trace.line("CHECK", "all tool URLs point at the mock" if not bad else "URLs NOT on the mock: " + ", ".join(bad))
    else:
        trace.line("CHECK", "tool URLs: " + ", ".join(urls))
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", help="case folder or brief files; a trailing http(s) URL is taken as the mock")
    ap.add_argument("--mock", help="base URL of the bank services mock the phone agent must call")
    ap.add_argument("--slot", help="label for the workflow on Freya (same slot = same workflow updated in place)")
    a = ap.parse_args()
    if not a.mock and a.inputs[-1].startswith("http"): a.mock = a.inputs.pop()
    files = collect_inputs(a.inputs)
    slot = a.slot or slot_for(a.inputs)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    trace = Trace(slot, stamp)
    t0 = time.time()
    trace.line("START", f"slot {slot}, builder model {MODEL}, skill {SKILL}, budget {BUDGET_MIN:.0f} min, mock {a.mock or '(kit tool API)'}")
    for f in files: trace.line("INPUT", str(f.relative_to(KIT)) if f.is_relative_to(KIT) else str(f))
    ws, docs = make_workspace(slot, files, stamp)
    trace.line("WORKDIR", f"{ws.relative_to(KIT)} (platform docs, Freya client, test tools, skill and the inputs only)")

    deadline = time.strftime("%H:%M", time.localtime(t0 + BUDGET_MIN * 60))
    prompt = (f"Use the {SKILL} skill to build the phone agent.\n\n"
              f"Slot: {slot}  (write out/{slot}.workflow.json and save it with this slot)\n"
              f"Mock base URL for every bank tool call: {a.mock or 'use the server URL in the tool API file'}\n"
              f"Hard stop at {deadline} local time ({BUDGET_MIN:.0f} minutes from now). Have a saved, working workflow long before that.\n"
              "Work only in this folder. Everything about this bank is in input/.\n\n"
              "Documents (read all of them):\n" + "\n".join(f"- {d.relative_to(ws)}" for d in docs))
    options = ClaudeAgentOptions(
        cwd=ws, model=MODEL, skills=[SKILL], setting_sources=["project"],
        allowed_tools=["Read", "Write", "Edit", "Glob", "Grep", "Bash"], permission_mode="dontAsk", max_turns=200,
        # Tests take up to 11 minutes and must run in the foreground: the builder stops when Claude ends its turn.
        env={"BASH_DEFAULT_TIMEOUT_MS": "900000", "BASH_MAX_TIMEOUT_MS": "1200000", "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1",
             "PATH": str(pathlib.Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", ""),
             "BUILDER_SLOT": slot, "BUILDER_MOCK_URL": a.mock or ""},
    )
    try:
        asyncio.run(asyncio.wait_for(run_claude(trace, prompt, options), timeout=BUDGET_MIN * 60))
    except asyncio.TimeoutError:
        trace.line("STOP", f"time budget of {BUDGET_MIN:.0f} min reached, exporting the last saved workflow")
    except Exception as e:
        trace.line("ERROR", f"builder crashed: {type(e).__name__}: {one_line(e, 300)}")
    merge_state_back(ws, slot)
    try:
        check_and_export(trace, slot, a.mock)
    except Exception as e:
        trace.line("ERROR", f"export failed: {type(e).__name__}: {one_line(e, 300)}")
    trace.line("END", f"{(time.time() - t0) / 60:.1f} min, {trace.model_calls} model calls. Trace: {trace.path}")


if __name__ == "__main__":
    main()
