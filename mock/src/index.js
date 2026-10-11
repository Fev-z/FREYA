// Mock of the bank's services on Cloudflare Workers.
// It speaks the kit's practice interface, so tools/run_cases.py works against it unchanged:
//   FREYA_BANK_HOST=https://<this worker> python3 tools/run_cases.py <agent_id> --brief A
//
// Tool calls (no key, the customer_id is the secret of one call):  POST /v1/<tool>
// Practice (header x-team-key):  POST /v1/practice/cases      [case, ...]   add or replace cases
//                                POST /v1/practice/sessions   {"case": id}  -> {"variables": {..., customer_id}}
//                                GET  /v1/practice/ledger/<customer_id>
// All state lives in one Durable Object, so every request sees the same ledger.
import BUNDLED_CASES from "../cases.json";

const MAX_WRONG = 3;

export default {
  async fetch(request, env) {
    const stub = env.BANK.get(env.BANK.idFromName("bank"));
    return stub.fetch(request);
  },
};

const json = (body, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

const isoDate = (s) => {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return null;
  const d = new Date(s + "T00:00:00Z");
  return isNaN(d) || d.toISOString().slice(0, 10) !== s ? null : s;
};

export class Bank {
  constructor(state, env) {
    this.storage = state.storage;
    this.env = env;
  }

  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "");
    let body = {};
    if (request.method === "POST") {
      try { body = await request.json(); } catch { return json({ ok: false, error: "body is not JSON" }, 400); }
    }
    if (path === "" || path === "/v1" || path === "/health") return json({ ok: true, service: "bank mock" });

    if (path.startsWith("/v1/practice/")) {
      if (!this.env.TEAM_KEY || request.headers.get("x-team-key") !== this.env.TEAM_KEY) return json({ ok: false, error: "bad team key" }, 401);
      return this.practice(path.slice("/v1/practice/".length), body);
    }

    const tool = path.replace(/^\/v1\//, "");
    if (!TOOLS[tool]) return json({ ok: false, error: `unknown tool ${tool}` }, 404);
    const cust = body.customer_id && (await this.storage.get("cust:" + body.customer_id));
    if (!cust) return json({ ok: false, error: "unknown customer_id" });

    // close_call is the last call: anything after it is refused and not written to the ledger
    if (cust.closed) return json({ ok: false, error: "call already closed" });
    let status = 200, result;
    const n = (cust.counts[tool] = (cust.counts[tool] || 0) + 1);
    const fault = (cust.case.faults || []).find((f) => f.tool === tool);
    if (fault && n <= (fault.fail_first_n || 0)) { status = 500; result = { ok: false, error: "service unavailable, nothing was recorded" }; }
    else result = TOOLS[tool](cust, body);
    cust.ledger.calls.push({ tool, body, result, status, at: new Date().toISOString() });
    await this.storage.put("cust:" + cust.customer_id, cust);
    return json(result, status);
  }

  async practice(route, body) {
    if (route === "cases") {
      const list = Array.isArray(body) ? body : body.cases || [];
      for (const c of list) await this.storage.put("case:" + c.id, c);
      return json({ ok: true, stored: list.map((c) => c.id) });
    }
    if (route === "sessions") {
      const c = (await this.storage.get("case:" + body.case)) || BUNDLED_CASES.find((x) => x.id === body.case);
      if (!c) return json({ ok: false, error: `unknown case ${body.case}` }, 404);
      const customer_id = "c_" + crypto.randomUUID().replace(/-/g, "").slice(0, 16);
      const cust = {
        customer_id, case: c, counts: {}, closed: false,
        id: { verified: {}, wrong: 0 },
        ledger: { outcome: null, reason: null, promises: [], notes: [], callbacks: [], transfers: [], calls: [] },
      };
      await this.storage.put("cust:" + customer_id, cust);
      return json({ ok: true, variables: { ...c.variables, customer_id } });
    }
    if (route.startsWith("ledger/")) {
      const cust = await this.storage.get("cust:" + route.slice("ledger/".length));
      if (!cust) return json({ ok: false, error: "unknown customer_id" }, 404);
      return json({ customer_id: cust.customer_id, case: cust.case.id, ...cust.ledger });
    }
    return json({ ok: false, error: `unknown practice route ${route}` }, 404);
  }
}

const verified = (cust) => Object.keys(cust.case.identity).every((f) => cust.id.verified[f]);
const products = (cust) => cust.case.products.map((p, i) => ({ product_id: "p" + (i + 1), ...p }));
const needId = (cust) => (verified(cust) ? null : { ok: false, error: "identity not verified" });
const productOf = (cust, pid) => products(cust).find((p) => p.product_id === pid);

const TOOLS = {
  verify_identity(cust, { field, answer }) {
    const fields = Object.keys(cust.case.identity);
    if (!fields.includes(field)) return { ok: false, error: `field must be one of ${fields.join(", ")}` };
    const left = () => Math.max(0, MAX_WRONG - cust.id.wrong);
    if (cust.id.wrong >= MAX_WRONG) return { ok: false, error: "identity check ended after three wrong answers", verified: false, wrong_answers_left: 0, all_verified: false };
    const want = String(cust.case.identity[field]);
    let got = String(answer ?? "").trim();
    let hint;
    if (/date/.test(field)) {
      if (!isoDate(got)) return { ok: false, error: "answer is not a date in YYYY-MM-DD", wrong_answers_left: left(), all_verified: verified(cust) };
      const [y, m, d] = got.split("-");
      if (got !== want && `${y}-${d}-${m}` === want && d !== m) hint = "day_month_swapped";
    } else if (/^\d+$/.test(want)) {
      got = got.replace(/\D/g, "");
    } else {
      got = got.toLowerCase().replace(/\s+/g, ""); // postcodes and other codes: case and spaces do not matter
    }
    const ok = got === (/^\d+$/.test(want) || /date/.test(field) ? want : want.toLowerCase().replace(/\s+/g, ""));
    if (ok) cust.id.verified[field] = true;
    else if (!hint) cust.id.wrong += 1; // a day/month swap is not a wrong answer
    const r = { ok: true, verified: ok, wrong_answers_left: left(), all_verified: verified(cust) };
    if (hint) r.hint = hint;
    return r;
  },

  get_account(cust) {
    return needId(cust) || { ok: true, products: products(cust) };
  },

  create_promise(cust, { product_id, amount, date }) {
    const no = needId(cust); if (no) return no;
    if (!productOf(cust, product_id)) return { ok: false, error: "unknown product_id" };
    if (cust.ledger.promises.some((p) => p.product_id === product_id)) return { ok: false, error: "a promise is already recorded for this product" };
    if (!(Number(amount) > 0)) return { ok: false, error: "amount must be a positive number" };
    if (!isoDate(String(date))) return { ok: false, error: "date must be YYYY-MM-DD" };
    const promise_id = "pr_" + (cust.ledger.promises.length + 1);
    cust.ledger.promises.push({ promise_id, product_id, amount: Number(amount), date });
    return { ok: true, promise_id };
  },

  add_note(cust, { product_id, reason, text }) {
    if (product_id && !productOf(cust, product_id)) return { ok: false, error: "unknown product_id" };
    if (!reason) return { ok: false, error: "reason is required" };
    cust.ledger.notes.push({ product_id, reason, text: text || "" });
    return { ok: true };
  },

  schedule_callback(cust, { date, time }) {
    if (!isoDate(String(date)) || !/^\d{2}:\d{2}$/.test(String(time))) return { ok: false, error: "date must be YYYY-MM-DD and time HH:MM" };
    cust.ledger.callbacks.push({ date, time });
    return { ok: true };
  },

  transfer_to_agent(cust, { queue }) {
    if (!queue) return { ok: false, error: "queue is required" };
    cust.ledger.transfers.push({ queue });
    return { ok: true };
  },

  close_call(cust, { outcome, reason }) {
    if (!outcome) return { ok: false, error: "outcome is required" };
    cust.ledger.outcome = outcome;
    cust.ledger.reason = reason || null;
    cust.closed = true;
    return { ok: true };
  },
};
