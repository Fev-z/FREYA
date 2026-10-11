"""Where do we lose score? Reads run_cases.py --out files and groups every failure into a cause bucket.

    python3 evals/analyze_failures.py results/a.json results/b.json ...

Prints, per file: pass count, and per failed case the buckets; then a total table of buckets across files.
Buckets come from the ledger reasons that score.py writes and from keywords in the judge's explanation.
"""
import collections, json, re, sys

LEDGER = [
    ("outcome/reason wrong", r"^outcome \("),
    ("promise wrong/missing/extra", r"^promises "),
    ("notes wrong", r"^notes "),
    ("callback wrong", r"^callbacks "),
    ("transfer wrong", r"^transfers "),
    ("close_call missing/not last", r"not closed with close_call"),
    ("account tool before identity", r"before identity was verified"),
    ("identity tools on third party", r"customer was not on the line"),
]
JUDGE = [
    ("judge: repeated offer/question", r"(twice|three times|more than once|repeated|again and again|only once)"),
    ("judge: 'recorded' / false success claim", r"(recorded|claim(ed)? .*success|before a successful)"),
    ("judge: disclosure before identity / to third party", r"(before identity|third party|relative|disclos|reason for the call|names no product)"),
    ("judge: missing required sentence", r"(text message|sentence|did not say|failed to (say|mention|state)|not mention)"),
    ("judge: persuasion/attempt count", r"(persuasion|attempt)"),
    ("judge: read-back/confirmation", r"(read.?back|confirm)"),
    ("judge: amount rule (floor/ask how much)", r"(floor|minimum|how much)"),
    ("judge: date rule (deadline/holiday/weekday)", r"(deadline|holiday|business day|weekend|friday|monday|october)"),
    ("judge: sympathy/hardship handling", r"(sympathy|hardship|support team)"),
    ("judge: call ended early / silence", r"(ended prematurely|terminated|hung up|no response|silent)"),
    ("judge: offered forbidden term (discount/plan)", r"(discount|waiver|plan)"),
]


def buckets(reason):
    out = []
    for name, pat in LEDGER:
        if re.search(pat, reason):
            out.append(name)
    if reason.startswith("conversation:"):
        text = reason.lower()
        # the judge lists what passed too; keep only the part that explains the failure
        if "however" in text:
            text = text.split("however", 1)[1]
        for cut in ("all other", "the other criteria", "while it correctly", "although the agent correctly", "although"):
            if cut in text and text.index(cut) > 40:
                text = text.split(cut, 1)[0]
        text = re.split(r"(?<=\.)\s+(?=-|\d\.|the assistant correctly|no persuasion|no discounts|no promise was recorded, which)", text)[0] if text.startswith(" -") is False else text
        hit = [name for name, pat in JUDGE if re.search(pat, text)]
        out += hit or ["judge: other"]
    return out or ["other"]


def main(paths):
    total = collections.Counter()
    for p in paths:
        d = json.load(open(p, encoding="utf-8"))
        runs = d.get("all_rows") or [d.get("rows", [])]
        print(f"\n== {p}: agent {d.get('agent_id')}, {len(runs)} run(s)")
        per_case = collections.defaultdict(list)
        for run in runs:
            for r in run:
                per_case[r["id"]].append(r)
        for cid, rs in per_case.items():
            passes = sum(r["pass"] for r in rs)
            if passes == len(rs):
                continue
            bs = collections.Counter(b for r in rs if not r["pass"] for f in r["failed"] for b in buckets(f))
            total.update(bs)
            first = next(f for r in rs if not r["pass"] for f in r["failed"])
            print(f"  {cid} {passes}/{len(rs)}  {dict(bs)}\n      e.g. {first[:220]}")
        ok = sum(all(r["pass"] for r in rs) for rs in per_case.values())
        print(f"  => {ok}/{len(per_case)} cases pass in every run")
    print("\n== failure buckets across all files")
    for b, n in total.most_common():
        print(f"  {n:3d}  {b}")


if __name__ == "__main__":
    main(sys.argv[1:])
