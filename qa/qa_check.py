"""End-to-end QA of one builder run: the exported workflow and its trace, against the QA checklist
(docs/research/benzer_pipelinelar.md section B, conduct.md, the skill's rules).

    python3 qa/qa_check.py submission/<slot>.workflow.json traces/<stamp>-<slot>.log [--api tools/openapi.json] [--base <mock url>]

Prints PASS / WARN / FAIL per check. Static only: behaviour is measured with tools/run_cases.py and evals/run_edge.py.
"""
import argparse, json, os, re, subprocess, sys

RECORD_WORDS = re.compile(r"\b(recorded|kaydedil\w*|kayded\w*)\b", re.I)


def checks(wf, trace_text, api_path, base):
    out = []
    nodes = wf.get("nodes", {})
    gnodes = wf.get("global_nodes") or {}

    def add(level, name, detail=""):
        out.append((level, name, detail))

    # lint
    if api_path:
        args = [sys.executable, os.path.join(os.path.dirname(__file__), "lint.py"), "-", api_path]
        tmp = os.path.join(os.path.dirname(__file__), "_wf.json")
        json.dump(wf, open(tmp, "w", encoding="utf-8"))
        args[2] = tmp
        if base:
            args += ["--base", base]
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
        os.remove(tmp)
        last = (r.stdout.strip().splitlines() or ["?"])[-1]
        errs = [l for l in r.stdout.splitlines() if l.startswith("ERROR")]
        add("FAIL" if errs else "PASS", "lint", last + ("; " + " | ".join(errs[:3]) if errs else ""))

    # opening line
    init = nodes.get(wf.get("initial_node"), {})
    seen, k = set(), wf.get("initial_node")
    while init and init.get("node_type") != "conversation" and k not in seen:
        seen.add(k)
        k = init.get("passthrough_default_transition") or ((init.get("transitions") or [{}])[-1].get("target_node"))
        init = nodes.get(k, {})
    opening = (init.get("on_enter") or {}).get("text") or ""
    add("FAIL" if RECORD_WORDS.search(opening) else "PASS", "opening avoids the success word ('recorded'/'kaydedildi')", opening[:140])
    leak = [w for w in ("collection", "debt", "overdue", "past due", "borç", "tahsilat", "gecik") if w in opening.lower()]
    add("FAIL" if leak else "PASS", "opening does not mention the debt", ",".join(leak))

    # silent conversation steps
    silent = [k for k, n in nodes.items() if n.get("node_type") == "conversation" and (n.get("on_enter") or {}).get("type") == "silent"]
    add("FAIL" if silent else "PASS", "no conversation step has a silent entry", ",".join(silent))

    # interrupts and conduct
    add("PASS" if gnodes else "WARN", "global interrupt nodes present", f"{len(gnodes)}: {', '.join(gnodes)}")
    sp = (wf.get("system_prompt") or "").lower()
    add("PASS" if any(w in sp for w in ("invent", "uydur", "never claim", "do not claim", "honest")) else "WARN",
        "system prompt has the honesty rule", "")
    add("PASS" if len(sp) > 200 else "WARN", "system prompt carries global rules", f"{len(sp)} chars")

    # tools
    names = []
    hooks_post = {}
    for n in list(nodes.values()) + list(gnodes.values()):
        for t in (n.get("tools") or []) + (n.get("pre_actions") or []):
            f = t.get("function", {})
            names.append(f.get("name"))
            hooks_post[f.get("name")] = bool(t.get("post_process_code"))
    for t in wf.get("tools") or []:
        names.append(t.get("function", {}).get("name"))
    for tool in ("verify_identity", "create_promise"):
        if tool in names:
            add("PASS" if hooks_post.get(tool) else "WARN", f"{tool} has a post-hook (what_to_do_next / failure shapes)", "")
    lifecycle = [t for t in (wf.get("tools") or []) if (t.get("config") or {}).get("alwaysRunsAt")]
    add("PASS" if lifecycle else "WARN", "close tool is engine-run (lifecycle) or otherwise guaranteed", f"{len(lifecycle)} lifecycle tool(s)")
    code_nodes = [k for k, n in nodes.items() if n.get("node_type") == "code"]
    hook_writers = [f.get("name") for n in list(nodes.values()) + list(gnodes.values())
                    for t in (n.get("tools") or []) + (n.get("pre_actions") or [])
                    for f in [t.get("function", {})]
                    if "vars[" in (t.get("pre_process_code") or "") + (t.get("post_process_code") or "")]
    add("PASS" if code_nodes or hook_writers else "WARN", "decisions computed in code nodes or hooks that write variables",
        ",".join(code_nodes + hook_writers))
    model_writes = [k for k, n in nodes.items() for t in (n.get("tools") or []) if t.get("function", {}).get("name") == "create_promise"]
    add("PASS" if not model_writes else "WARN", "promise write is engine-run after a code check (not a model tool)",
        ("model holds create_promise in: " + ",".join(model_writes)) if model_writes else "")

    # trace
    if trace_text is not None:
        for tag in ("START", "END", "FREYA", "MODEL"):
            add("PASS" if f" {tag} " in trace_text or f"  {tag}" in trace_text else "FAIL", f"trace has {tag} lines", "")
        add("PASS" if re.search(r"\d+ / \d+ passed", trace_text) else "WARN", "trace records a self-test result", "")
        add("FAIL" if "ERROR" in trace_text else "PASS", "trace has no ERROR line",
            next((l[:160] for l in trace_text.splitlines() if "ERROR" in l), ""))
        key = os.environ.get("FREYA_API_KEY", "")
        add("FAIL" if key and key in trace_text else "PASS", "trace contains no API key", "")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workflow")
    ap.add_argument("trace", nargs="?")
    ap.add_argument("--api", default="tools/openapi.json")
    ap.add_argument("--base")
    a = ap.parse_args()
    d = json.load(open(a.workflow, encoding="utf-8"))
    wf = d.get("workflow", d)
    trace = open(a.trace, encoding="utf-8", errors="replace").read() if a.trace else None
    res = checks(wf, trace, a.api, a.base)
    for level, name, detail in res:
        print(f"{level:<4} {name}" + (f"  [{detail}]" if detail else ""))
    print(f"\nQA: {sum(l == 'FAIL' for l, _, _ in res)} FAIL, {sum(l == 'WARN' for l, _, _ in res)} WARN, {sum(l == 'PASS' for l, _, _ in res)} PASS")


if __name__ == "__main__":
    main()
