"""Static checks for a Freya workflow JSON before it is saved.

    python3 builder/lint.py out/<slot>.workflow.json <tool_api_path>

Prints one line per problem and exits 1 if any ERROR was found. Warnings do not fail.
The checks come from docs/workflow-format.md and docs/tools-and-code.md: things the platform
drops silently or that dead-lock a call.
"""
import json, re, sys
from urllib.parse import urlparse

WRITE_TOOLS = {"create_promise", "add_note", "schedule_callback", "transfer_to_agent", "close_call"}


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def walk_nulls(x, path, out):
    if x is None:
        out.append(("WARN", f"null value at {path} (docs say the schema rejects null; omit the field or use \"\")"))
    elif isinstance(x, dict):
        for k, v in x.items():
            walk_nulls(v, f"{path}.{k}", out)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            walk_nulls(v, f"{path}[{i}]", out)


def tool_list(wf):
    """(where, tool) for every tool function in the workflow."""
    for key, n in {**wf.get("nodes", {}), **wf.get("global_nodes", {})}.items():
        for t in n.get("tools", []) or []:
            yield f"node {key} tools", t
        for t in n.get("pre_actions", []) or []:
            yield f"node {key} pre_actions", t
    for t in wf.get("tools", []) or []:
        yield "workflow tools", t


def lint(wf, api):
    out = []
    walk_nulls(wf, "workflow", out)
    nodes = wf.get("nodes", {})
    gnodes = wf.get("global_nodes", {}) or {}
    allk = set(nodes) | set(gnodes)
    if wf.get("initial_node") not in nodes:
        out.append(("ERROR", f"initial_node {wf.get('initial_node')!r} is not a node"))
    if "agent_config" in wf:
        out.append(("WARN", "agent_config present: leave it out (README)"))

    server = (api.get("servers") or [{}])[0].get("url", "")
    host = urlparse(server).netloc
    paths = {p.strip("/"): spec for p, spec in api.get("paths", {}).items()}

    # nodes
    for key, n in {**nodes, **gnodes}.items():
        nt = n.get("node_type")
        if n.get("name") != key:
            out.append(("WARN", f"node {key}: name {n.get('name')!r} differs from key"))
        if nt != "conversation" and n.get("tools"):
            out.append(("ERROR", f"node {key}: tools on a {nt} node are dropped by the platform"))
        if nt == "conversation" and n.get("pre_actions"):
            out.append(("ERROR", f"node {key}: pre_actions on a conversation node are dropped"))
        for tr in n.get("transitions", []) or []:
            tgt = tr.get("target_node")
            if tgt not in allk and tgt != "__previous__":
                out.append(("ERROR", f"node {key}: transition to unknown node {tgt!r}"))
            cond = tr.get("condition") or {}
            if cond.get("logic") == "and":
                out.append(("ERROR", f"node {key}: top-level condition logic must be 'or'"))
        if n.get("passthrough"):
            trs = n.get("transitions") or []
            if not trs or (trs[-1].get("condition") or {}).get("operator") != "always":
                out.append(("ERROR", f"node {key}: passthrough node must end with an 'always' transition"))
        if nt == "end_call":
            if n.get("transitions"):
                out.append(("ERROR", f"node {key}: end_call node must have transitions: []"))
            if not (n.get("terminal") or {}).get("function"):
                out.append(("ERROR", f"node {key}: end_call node without terminal.function"))
        if nt == "conversation":
            if not n.get("transitions") and key not in gnodes:
                out.append(("WARN", f"node {key}: conversation node with no transitions (call can only end by hang-up)"))
            if n.get("max_node_turns") and not n.get("max_turn_transition"):
                out.append(("WARN", f"node {key}: max_node_turns without max_turn_transition has no effect"))
            if not n.get("tools") and "tool" not in (n.get("task_message") or "").lower():
                out.append(("WARN", f"node {key}: no tools; say in task_message that no tool call is allowed"))
        for ex in n.get("extraction_schema", []) or []:
            if "min_confidence" not in ex:
                out.append(("WARN", f"node {key}: extraction {ex.get('name')} has no min_confidence (default 0.95 is strict)"))
            if "extraction_prompt" in ex and "{{extractor.speech}}" not in ex["extraction_prompt"]:
                out.append(("ERROR", f"node {key}: extraction_prompt without {{{{extractor.speech}}}} sees nothing"))

    # reachability: every node reachable from initial reaches an end_call node
    graph = {k: [t.get("target_node") for t in (n.get("transitions") or [])] + ([n["max_turn_transition"]] if n.get("max_turn_transition") else []) for k, n in nodes.items()}
    seen, stack = set(), [wf.get("initial_node")]
    while stack:
        k = stack.pop()
        if k in seen or k not in graph:
            continue
        seen.add(k)
        stack += graph[k]
    for k in set(nodes) - seen:
        if k not in gnodes:
            out.append(("WARN", f"node {k}: not reachable from initial_node"))
    ends = {k for k, n in nodes.items() if n.get("node_type") == "end_call"}
    if not ends:
        out.append(("WARN", "no end_call node: calls end only when the customer hangs up"))

    # tools
    close_calls = 0
    for where, t in tool_list(wf):
        f = t.get("function", {})
        name, handler = f.get("name"), f.get("handler")
        props = (f.get("parameters") or {}).get("properties", {})
        if handler == "__function__:api_call":
            url = (props.get("url") or {}).get("default", "")
            if "const" in json.dumps(props):
                out.append(("ERROR", f"{where} {name}: uses 'const' (never sent; use 'default')"))
            if urlparse(url).netloc != host:
                out.append(("ERROR", f"{where} {name}: url {url!r} is not on the tool API host {host!r} (calls elsewhere fail the case)"))
            path = url.split(host, 1)[-1].strip("/")
            base_path = urlparse(server).path.strip("/")
            ep = path[len(base_path):].strip("/") if base_path and path.startswith(base_path) else path
            spec = paths.get(ep)
            if spec is None:
                out.append(("ERROR", f"{where} {name}: endpoint {ep!r} not in tool API"))
            else:
                schema = spec["post"]["requestBody"]["content"]["application/json"]["schema"]
                want = schema.get("properties", {})
                body = (props.get("body") or {}).get("properties", {})
                for fld in body:
                    if fld not in want:
                        out.append(("ERROR", f"{where} {name}: body field {fld!r} not in the API schema {sorted(want)}"))
                for fld in schema.get("required", []):
                    if fld not in body:
                        out.append(("ERROR", f"{where} {name}: required API field {fld!r} missing from body"))
                for fld, fs in body.items():
                    if fld in want and "enum" in want[fld] and "enum" in fs and set(fs["enum"]) - set(want[fld]["enum"]):
                        out.append(("ERROR", f"{where} {name}: enum for {fld} has values not in the API: {sorted(set(fs['enum']) - set(want[fld]['enum']))}"))
                cid = (body.get("customer_id") or {}).get("default")
                if "customer_id" in want and cid != "{{customer_id}}":
                    out.append(("ERROR", f"{where} {name}: customer_id must be baked as default '{{{{customer_id}}}}'"))
            if ep in WRITE_TOOLS and (t.get("config") or {}).get("maxRetries", 0) not in (0, None):
                out.append(("WARN", f"{where} {name}: write tool with maxRetries>0 can record twice"))
            if ep == "close_call":
                close_calls += 1
            for hook in ("pre_process_code", "post_process_code"):
                if hook in t and ("{{" in t[hook] or "}}" in t[hook]):
                    out.append(("ERROR", f"{where} {name}: {hook} contains '{{{{' or '}}}}'"))
            if where.endswith(" tools") and not where.startswith("workflow") and len(f.get("description", "")) < 25:
                out.append(("WARN", f"{where} {name}: short description; say WHEN to call it"))
        if handler == "__function__:code_exec":
            code = (props.get("code") or {}).get("default", "")
            if "{{" in code or "}}" in code:
                out.append(("ERROR", f"{where} code_exec: code contains '{{{{' or '}}}}'"))
            try:
                compile(code, "code_exec", "exec")
            except SyntaxError as e:
                out.append(("ERROR", f"{where} code_exec: Python syntax error: {e}"))
    if close_calls == 0:
        out.append(("ERROR", "no close_call tool anywhere: every call must end with exactly one close_call"))
    elif close_calls > 1:
        out.append(("WARN", f"{close_calls} close_call tools: make sure only one can ever run in a call"))

    # transitions that test an extracted enum must use one of its values
    for key, n in {**nodes, **gnodes}.items():
        enums = {e["name"]: set(map(str, e.get("enum_values", []))) for e in (n.get("extraction_schema") or []) if e.get("enum_values")}
        for tr in n.get("transitions", []) or []:
            for c in _leaf_conditions(tr.get("condition") or {}):
                v, op = c.get("variable"), c.get("operator")
                if v in enums and op in ("equals", "not_equals") and str(c.get("operand")) not in enums[v]:
                    out.append(("ERROR", f"node {key}: transition tests {v} == {c.get('operand')!r}, not one of its enum values {sorted(enums[v])}"))

    # every {{var}} used in a prompt or fixed line should be set by something
    known = set((wf.get("test_variables") or {}).keys())
    for n in {**nodes, **gnodes}.values():
        known |= {e["name"] for e in (n.get("extraction_schema") or [])}
        known |= {m["variable"] for m in (n.get("response_mapping") or [])}
        for _, t in [(None, x) for x in (n.get("tools") or []) + (n.get("pre_actions") or [])]:
            known |= {m["variable"] for m in (t.get("response_mapping") or [])}
    blob = json.dumps(wf)
    known |= set(re.findall(r"vars\[\\?['\"](\w+)\\?['\"]\]\s*=", blob))
    # code that builds names dynamically (v[k + 'floor']): accept any quoted literal used in code as a name or suffix
    code_literals = set()
    for _, t in tool_list(wf):
        props = ((t.get("function") or {}).get("parameters") or {}).get("properties", {})
        code = (props.get("code") or {}).get("default", "") + t.get("pre_process_code", "") + t.get("post_process_code", "")
        code_literals |= set(re.findall(r"['\"](\w{3,})['\"]", code))
    known |= {v for v in code_literals}
    for key, n in {**nodes, **gnodes}.items():
        texts = [n.get("task_message") or "", n.get("loop_prompt") or "", (n.get("on_enter") or {}).get("text") or ""]
        for txt in texts:
            for var in re.findall(r"\{\{\s*([\w.\-]+)(?::json)?\s*\}\}", txt):
                root = var.split(".")[0]
                if root in ("system", "call", "date", "time", "extractor") or root.endswith("_response") or root.endswith("_args") or "." in var and root in known:
                    continue
                if root not in known and not any(root.endswith(s) for s in code_literals):
                    out.append(("WARN", f"node {key}: prompt uses {{{{{var}}}}} but nothing visibly sets it (the model would see the literal placeholder)"))

    # nothing about the debt in the very first fixed line
    first = nodes.get(wf.get("initial_node"), {})
    seen_first, k = set(), wf.get("initial_node")
    while first and first.get("node_type") != "conversation" and k not in seen_first:   # skip leading code/api nodes
        seen_first.add(k)
        k = first.get("passthrough_default_transition") or ((first.get("transitions") or [{}])[-1].get("target_node"))
        first = nodes.get(k, {})
    opening = ((first.get("on_enter") or {}).get("text") or "").lower()
    leak = [w for w in ("collection", "debt", "overdue", "past due", "payment", "owe", "arrears") if w in opening]
    if leak:
        out.append(("WARN", f"opening line mentions {leak}: most briefs forbid this before identity is verified"))
    return out


def _leaf_conditions(c):
    if "conditions" in c:
        for sub in c["conditions"]:
            yield from _leaf_conditions(sub)
    elif c:
        yield c


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    wf = load(sys.argv[1])
    wf = wf.get("workflow", wf) if "nodes" not in wf else wf
    out = lint(wf, load(sys.argv[2]))
    for level, msg in out:
        print(f"{level}: {msg}")
    errs = sum(1 for l, _ in out if l == "ERROR")
    print(f"lint: {errs} errors, {len(out) - errs} warnings")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
