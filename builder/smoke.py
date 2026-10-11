"""Chat smoke test for a saved workflow: does the call start, and does the opening leak nothing?

    python3 builder/smoke.py <workflow_id> [--vars '{"customer_id": "...", ...}'] [--turn "Yes, speaking."]...

Talks to the published workflow through POST /api/v2/chat/message, one turn at a time. No simulation, no queue.
Uses the workflow's own test_variables unless --vars is given. Prints the agent's replies and a verdict line.
This is the self-test the builder can run on a brief that has no practice customers.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import freya

LEAK = ["collection", "debt", "overdue", "past due", "past-due", "owe", "payment", "loan", "credit card", "balance", "arrears", "late"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workflow_id")
    ap.add_argument("--vars")
    ap.add_argument("--turn", action="append", default=[])
    a = ap.parse_args()
    variables = json.loads(a.vars) if a.vars else None
    if variables is None:
        w = freya.api("GET", f"/api/v2/workflow/{a.workflow_id}", workspaceId=freya.workspace_id())["workflow"]["workflow"]
        variables = w.get("test_variables") or {}
    turns = ["Hello?"] + (a.turn or ["Yes, speaking."])
    call_id, replies, problems = None, [], []
    for i, msg in enumerate(turns):
        body = {"workflowId": a.workflow_id, "message": msg, "customerVariables": variables}
        if call_id:
            body["callId"] = call_id
        try:
            r = freya.api("POST", "/api/v2/chat/message", body)
        except RuntimeError as e:
            problems.append(f"turn {i + 1} failed: {str(e)[:300]}")
            break
        call_id = r.get("callId") or call_id
        reply = r.get("response") or ""
        replies.append(reply)
        print(f"CUSTOMER: {msg}\nAGENT: {reply}\n", flush=True)
        if not reply.strip():
            problems.append(f"turn {i + 1}: empty reply")
        if i == 0:
            low = reply.lower()
            leaked = [w for w in LEAK if w in low]
            if leaked:
                problems.append(f"opening mentions {leaked} before identity is checked")
            if "{{" in reply:
                problems.append("unresolved {{variable}} in the reply")
    if call_id:
        try:
            freya.api("POST", "/api/v2/chat/end", {"callId": call_id})
        except RuntimeError:
            pass
    print("SMOKE " + ("PASS" if not problems else "FAIL: " + "; ".join(problems)))
    sys.exit(0 if not problems else 1)


if __name__ == "__main__":
    main()
