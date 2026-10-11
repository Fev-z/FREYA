"""Smoke test for the bank mock: one session per case, the identity check, the account, a promise, the ledger.

    python3 mock/smoke.py https://<worker>.workers.dev [case_id ...]

Needs FREYA_BANK_TEAM_KEY. Uses the cases in mock/cases.json. Exits 1 on the first broken step.
"""
import json, os, pathlib, sys, urllib.request, urllib.error

HOST = sys.argv[1].rstrip("/").removesuffix("/v1") if len(sys.argv) > 1 else sys.exit(__doc__)
CASES = json.loads((pathlib.Path(__file__).parent / "cases.json").read_text())
ONLY = sys.argv[2:] or [CASES[0]["id"]]


def call(path, body=None):
    h = {"content-type": "application/json", "user-agent": "mock-smoke/0.1", "x-team-key": os.environ["FREYA_BANK_TEAM_KEY"]}
    req = urllib.request.Request(HOST + path, data=json.dumps(body).encode() if body is not None else None, headers=h, method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as r: return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def check(ok, what, got):
    print(("ok   " if ok else "FAIL ") + what + ("" if ok else f"  -> {got}"))
    if not ok: sys.exit(1)


status, health = call("/health")
check(status == 200, "health", health)
for cid in ONLY:
    case = next(c for c in CASES if c["id"] == cid)
    status, s = call("/v1/practice/sessions", {"case": cid})
    check(status == 200 and "customer_id" in s.get("variables", {}), f"{cid} session", s)
    cust = s["variables"]["customer_id"]
    status, r = call("/v1/get_account", {"customer_id": cust})
    check(r.get("ok") is False, f"{cid} account refused before identity", r)
    for field, answer in case["identity"].items():
        status, r = call("/v1/verify_identity", {"customer_id": cust, "field": field, "answer": str(answer)})
        check(r.get("verified") is True, f"{cid} verify {field}", r)
    check(r.get("all_verified") is True, f"{cid} all verified", r)
    status, r = call("/v1/get_account", {"customer_id": cust})
    check(r.get("ok") is True and r.get("products"), f"{cid} account after identity", r)
    p = r["products"][0]
    for attempt in (1, 2):                                   # a fault case fails first, then records
        status, r = call("/v1/create_promise", {"customer_id": cust, "product_id": p["product_id"], "amount": p["past_due"], "date": case["variables"]["now"][:10]})
        if r.get("ok"): break
    check(r.get("ok") is True, f"{cid} promise", r)
    status, r = call("/v1/close_call", {"customer_id": cust, "outcome": "promise"})
    check(r.get("ok") is True, f"{cid} close", r)
    status, led = call(f"/v1/practice/ledger/{cust}")
    check(led.get("outcome") == "promise" and len(led.get("promises", [])) == 1 and led["calls"][-1]["tool"] == "close_call", f"{cid} ledger", led)
print("mock OK")
