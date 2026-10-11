"""Small helpers that build valid Freya workflow pieces. Brief-independent: no rule, value or wording of any brief.

Use them in the per-brief generator script you write (out/gen_<slot>.py) so the JSON shapes are always right:

    import sys, json; sys.path.insert(0, 'builder')
    from lib import wfkit
    api = json.load(open('<tool_api.json>'))
    BASE = wfkit.api_base(api)                       # server URL from the tool API file, with a trailing '/'
    t = wfkit.api_tool(BASE, 'create_promise', 'CALL it only after ...', {...body fields from the API...}, ['product_id', ...])

Shapes follow docs/workflow-format.md and docs/tools-and-code.md (verified patterns): customer_id baked as
{{customer_id}}, every body field a leaf under body.properties, write tools maxRetries 0, passthrough code nodes
ending with an 'always' transition, end_call nodes with the farewell in terminal.spoken_message.
"""
import json

HDR = {"type": "object", "properties": {"Content-Type": {"type": "string", "default": "application/json"}}}


def api_base(api):
    url = (api.get("servers") or [{}])[0].get("url", "")
    return url if url.endswith("/") else url + "/"


def api_body_fields(api, endpoint):
    """The request body schema of one endpoint of the tool API file: (properties, required)."""
    for path, spec in api.get("paths", {}).items():
        if path.strip("/") == endpoint:
            s = spec["post"]["requestBody"]["content"]["application/json"]["schema"]
            return s.get("properties", {}), s.get("required", [])
    raise KeyError(endpoint)


def api_tool(base, name, desc, fields, required, max_retries=0, pre=None, post=None, mapping=None, timeout_ms=12000):
    """An api_call tool. `fields` are the body leaves except customer_id (baked here). Give each model-filled
    leaf a type, description, enum (copied from the API) and "default": "{{<field>}}" with a name no other
    variable uses; give fixed values a literal default."""
    props = {"customer_id": {"type": "string", "default": "{{customer_id}}"}}
    props.update(fields)
    t = {"type": "function", "config": {"timeoutMs": timeout_ms, "maxRetries": max_retries},
         "function": {"name": name, "handler": "__function__:api_call", "description": desc,
                      "parameters": {"type": "object", "properties": {
                          "url": {"type": "string", "default": base + name},
                          "method": {"type": "string", "default": "POST"},
                          "headers": HDR,
                          "body": {"type": "object", "properties": props, "required": required}}}}}
    if pre:
        t["pre_process_code"] = pre
    if post:
        t["post_process_code"] = post
    if mapping:
        t["response_mapping"] = mapping
    return t


def lifecycle_tool(tool, when="end_of_call"):
    """Turn an api_tool into a workflow-level lifecycle tool (put it in the workflow's top-level 'tools')."""
    t = json.loads(json.dumps(tool))
    t["config"]["alwaysRunsAt"] = [when]
    return t


def code_node(name, code, target):
    assert "{{" not in code and "}}" not in code, "code must not contain {{ or }}"
    compile(code, name, "exec")
    return {"name": name, "node_type": "code", "passthrough": True, "passthrough_default_transition": target,
            "on_enter": {"type": "silent"},
            "pre_actions": [{"type": "function", "function": {"name": "code_exec", "handler": "__function__:code_exec",
                             "parameters": {"type": "object", "properties": {
                                 "code": {"type": "string", "default": code},
                                 "timeout_ms": {"type": "number", "default": 10000}}}}}],
            "transitions": [{"target_node": target, "description": "always", "condition": {"operator": "always"}}]}


def api_node(name, tool, target, mapping=None, failure_target=None):
    """Passthrough api_request node that always runs `tool` on entry (engine-run, never skipped)."""
    trs = []
    if failure_target:
        trs.append({"target_node": failure_target, "description": "the call failed",
                    "condition": cond_gt(f"{name}_failure_count", 0)})
    trs.append({"target_node": target, "description": "always", "condition": {"operator": "always"}})
    return {"name": name, "node_type": "api_request", "passthrough": True, "passthrough_default_transition": target,
            "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True,
            "pre_actions": [tool], "response_mapping": mapping or [], "transitions": trs}


def end_node(name, fname, msg=""):
    """End the call. `fname` becomes the call's endedReason. With msg: a fixed farewell is said; without: silent."""
    props = {"message_mode": {"type": "string", "default": "custom" if msg else "none"}}
    if msg:
        props["spoken_message"] = {"type": "string", "default": msg}
    return {"name": name, "node_type": "end_call", "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True,
            "transitions": [],
            "terminal": {"type": "function", "function": {"name": fname, "handler": "__function__:end_call",
                         "parameters": {"type": "object", "properties": props}}}}


def setvars_code(values):
    """Code that writes fixed string values into vars (for example close_outcome / close_reason)."""
    lines = ["try:"] + [f"    vars[{k!r}] = {str(v)!r}" for k, v in values.items()] + ["except Exception:", "    pass", ""]
    return "\n".join(lines)


def cond_true(var):
    return {"logic": "or", "conditions": [{"variable": var, "operator": "equals", "operand": "true"},
                                          {"variable": var, "operator": "equals", "operand": "True"}]}


def cond_eq(var, val):
    return {"logic": "or", "conditions": [{"variable": var, "operator": "equals", "operand": val}]}


def cond_any_eq(pairs):
    """OR of (variable, value) equality checks."""
    return {"logic": "or", "conditions": [{"variable": v, "operator": "equals", "operand": x} for v, x in pairs]}


def cond_gt(var, n):
    return {"logic": "or", "conditions": [{"variable": var, "operator": "greater_than", "operand": n}]}


def cond_set(var):
    return {"logic": "or", "conditions": [{"variable": var, "operator": "is_set"}]}


def tr(target, desc, condition):
    return {"target_node": target, "description": desc, "condition": condition}


def intent(target, desc):
    return {"target_node": target, "description": desc, "condition": {"operator": "matches_intent", "description": desc}}


def stay(target):
    return {"target_node": target, "description": "stay in this step", "condition": {"operator": "always"}}


def conv(name, task, tools, transitions, on_enter=None, extraction=None, max_turns=60, first_entry_only=True):
    return {"name": name, "node_type": "conversation", "task_message": task, "tools": tools,
            "transitions": transitions, "max_node_turns": max_turns,
            "on_enter": on_enter or {"type": "llm"}, "extraction_schema": extraction or [],
            "on_enter_first_entry_only": first_entry_only}


def enum_extraction(name, values, description, min_confidence=0.6):
    return {"name": name, "type": "string", "enum_values": list(values), "description": description,
            "min_confidence": min_confidence}
