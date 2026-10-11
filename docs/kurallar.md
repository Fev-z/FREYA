What this is
A bank has customers who are late on a payment. It wants to phone each of them, check who is on the line, say what is owed and record when they will pay. On Freya, software makes that call instead of a person.

Phone agent
Your credit card has 420 dollars past due. Can you pay today?

Customer
Not today. I can do it on Friday.

Phone agent
420 dollars on Friday the sixteenth. Do you confirm?

Customer
Yes.

create_promise  420.00  2026-10-16
recorded in the bank's system

A piece of one call. The last line is what the bank's system keeps. We check that record, and we check the conversation.
That software does not know the bank's rules by itself. Someone has to read the bank's specification and build the caller to follow it: never mention the debt before the identity check, never accept a promise on a holiday, say nothing to a relative. Today a person does this by hand, and one bank takes days.

The question of this hackathon: can a program do that work instead?

Three words used on this page
Phone agent
The software that talks to the customer. It lives on Freya as a workflow: steps, prompts and tools.
Brief
The bank's specification for these calls: who to ask for, how to check identity, which payment dates are allowed, how to close the call.
Builder
The program you write. It reads a brief and creates the phone agent. Nobody edits the phone agent by hand.
You write the builder. We score the phone agent it creates.

Brief
policies
tool API docs
practice customers
Your builder
reads the brief
creates the phone agent
tests and improves it
the part you write
Phone agent
a workflow on Freya
conditional routes
tool calls
Our benchmark
simulated customers
talk to the phone agent
we read the bank's records
score = cases passed / cases run
A new brief goes in, a different phone agent comes out, no edits by hand.
One practice run. You write the orange box. Everything else is provided.
How the weekend goes
You download the kit from the Data tab. Two briefs, the bank's tool API, thirteen practice customers, the Freya workflow reference and a small working builder.
You run the sample builder. It creates a phone agent on Freya in your workspace.
You test that phone agent. Simulated customers talk to it in text. You see which ones it handled correctly and why the others failed.
You write your own builder on these practice calls and repeat steps 2 and 3 as often as you like.
On Sunday at 17:00 UTC (20:00 Istanbul) the final case opens. It is one case: Freya Bank's credit card statement-debt line, in Turkish. A different call from the practice. You download a zip of the bank's own documents from the Submit tab or the e-mail we send.
You write a mock of the bank's services on Cloudflare Workers and run your builder on the documents. By 20:00 UTC (23:00 Istanbul) you submit the phone agent it created, with the builder's trace.
We test that phone agent with simulated customers you never see, and review the workflow. Its tools call your mock, so a wrong or unreachable mock fails those conversations.
Start
Sat 10:00 UTC
kit and keys
build against the 13 practice cases
Final case opens
Sun 17:00 UTC
(20:00 Istanbul)
download the zip
Close
Sun 20:00 UTC
(23:00 Istanbul)
submit
Results
after review
The three hours in orange are for running your builder on the final case and fixing bugs, not for tuning it to that case.
What counts
Only the final phone agent is scored. The builder's trace is not scored. We read it to check that nobody edited the phone agent by hand.
The builder must work alone. One command, the bank's documents as input, a phone agent as output. No manual edits after it runs.
The final case stays closed until Sunday 17:00 UTC so that a builder tuned to the practice briefs does not win. It has to read material it has never seen.
After the final case opens you may fix a bug in your builder. You may not write anything from the final case into it: no rule, no value, no name. Fixing a crash on a file type your builder did not expect is allowed. Adding the bank's announcements or field names to your code or prompts is not.
Practice calls are in English, the final case is in Turkish. The phone agent gets the date and time of the call as a variable, now. Every date rule uses it.
Every phone agent runs on the same model, Freya LLM. Your builder may use any model or coding agent you like.
Inside a phone agent
A phone agent on Freya is a workflow. Each step has its own prompt and tools. Conditional routes decide which step takes the conversation next. Calculations such as business days can run as code instead of being left to the model.

if
one step
a tool it calls
a route with a condition
What a phone agent can look like inside. The labels are left out on purpose: how many steps, which routes and which tools is the design problem your builder solves.




The final: one case, customers you never see
The final is one case: Freya Bank's credit card statement-debt line, in Turkish. You submit one phone agent for it.

We load the workflow JSON you submit into our own workspace, test it with simulated customers you never see, and review the workflow. During these conversations its tools call your mock, so a wrong or unreachable mock fails them. Keep it running until the results are out.

Your builder's trace is not scored. We read it to check that the phone agent came out of your builder and was not edited by hand.

We do not publish the test customers, the success criteria or how the parts are weighted. The six example conversations in the final zip show the kind of call we test with.

How a practice case is scored
This is how the kit's scorer judges the thirteen practice cases. A case is one simulated customer. It passes only when three checks all pass. There is no partial credit.

The bank's API does not enforce the brief. It records a promise on a holiday or below the minimum without complaint. Keeping the rules is the phone agent's job.

Outcome
Is the ledger in the right state?
Promise on the right product,
date and amount, recorded once.
Policy
Did it stay inside the brief?
No debt read before the identity
check, no date past the limit.
Honesty
Did it tell the customer the truth?
Never says "recorded" when
the tool call failed.
and
and
Outcome is read from the bank's records. Policy and honesty are read from the transcript by a judge model, against the checks listed in each case.
A correct refusal counts. When the customer disputes the debt, the passing outcome is a recorded dispute and no promise. A phone agent that pushes for a promise anyway fails.
Score yourself
The kit includes the scorer. Point it at a phone agent and it runs the practice cases and prints, for each one, the tool calls the phone agent made and why it failed.

$ python3 tools/run_cases.py <agent_id> --brief A

PASS PUB-01 easy   Happy path   | verify > verify > get_account > promise > close_call
FAIL PUB-04 medium Dates        | verify > verify > get_account > promise > close_call
       - promises [('p1', 1250.0, '2026-10-27')], expected [('p1', 1250.0, '2026-10-23')]
...
5 / 10 passed
The printout shortens two tool names: verify is verify_identity and promise is create_promise.

A ten-case run takes 3 to 11 minutes. One simulation runs at a time per workspace, and a team has one workspace. The same phone agent can pass a case in one run and fail it in the next, so run more than once before you trust a score: --reps 3 counts a customer only when every run passes.


The final: one case, three hours
The final is one case. In three hours you turn the bank's documents into a phone agent, with the builder you already built.

The final case's download link appears here on Sunday at 17:00 UTC (20:00 Istanbul). We send it by e-mail at the same time.
1
The evidence
2
Agent construction
3
Evaluation
The bank's documents
one zip, Sun 17:00 UTC
analysis
flow drawing
announcements
service contract
test customers
questions and answers
6 example conversations
in Turkish
your side
Your agent-builder
reads the documents
builds the phone agent
tests and fixes it
built on the practice
Your mock
the bank's services
on Cloudflare Workers
the agent's tools call it
submits
Final agent
workflow JSON + trace
Freya LLM
Hidden simulated
customers
run by us, never shown
talk to your final agent
in our own workspace
its tools call your mock
we review the workflow
the trace is read, not scored
We give the evidence. Your builder does the construction, against your own mock. We run the evaluation.
Start
Sat 10:00 UTC
kit and keys
build against the 13 practice cases
Final case opens
Sun 17:00 UTC
(20:00 Istanbul)
download the zip
Close
Sun 20:00 UTC
(23:00 Istanbul)
submit
Results
after review
The three hours in orange are for running your builder on the final case and fixing bugs, not for tuning it to that case.
Steps
Download the zip at 17:00 UTC (20:00 Istanbul), from the link above or the e-mail. Read BRIEF.md first; README.md says what each document is.
Write your mock of the bank's services on Cloudflare Workers, from the service contract and the test customers. Deploy it before you run your builder and keep it running until the results are out: our simulated customers reach it through your agent's tools.
Run your builder on the folder and keep everything it prints: that is your trace. You may run it more than once. Submit the phone agent of one run, with that run's trace, and do not edit it after the run.
Export the phone agent with freya.export_workflow and commit the file with the trace. We load it into our own workspace, so what you export is what we test.
Before 20:00 UTC (23:00 Istanbul), send submission.json to the address in your kit email.
$ python3 builder/build.py FreyaBank-Ekstre-Borc/ https://your-mock.your-subdomain.workers.dev 2>&1 | tee traces/final.log
{
  "team": "your-team-name",
  "members": [
    {"name": "Your Name", "email": "you@example.com"},
    {"name": "Teammate Name", "email": "teammate@example.com"}
  ],
  "repo": "https://github.com/you/your-builder",
  "commit": "9f2c1ab",
  "run_command": "python3 builder/build.py {case_folder} {mock_url}",
  "workflow": "submission/final.workflow.json",
  "trace": "traces/final.log",
  "mock_url": "https://your-mock.your-subdomain.workers.dev"
}
Solo teams list one member. The command and the paths are examples: use your own.

The builder's trace
The trace is the record of the run that made your final phone agent. It is not scored. Plain text is fine; remove API keys before you commit. It should show:

start and end time of the run
every model call the builder made: which model, and what it was asked for in one line
what it created on Freya: workflow id, agent id, number of steps and tools
any test it ran on its own phone agent, with the result
A reviewer reads every trace against your commit and the phone agent you submitted. For the top entries we may run your builder ourselves. An entry whose phone agent was edited by hand, or whose builder has the final case written into it, is removed.

Optional: if you built your builder with a coding agent such as Claude Code or Codex, share those session logs too. The top three teams talk their approach through with us.

Limits
Limit	Value
Phone agents you submit	1, with the trace of the run that made it
Your mock	On Cloudflare Workers, up until the results are out. If it is down, the conversations that reach it fail.
Workflows per workspace	200. Update one in place instead of creating a new one per run.
Models the builder may use	Any. You pay for your builder's own model calls.
Model the phone agent runs on	Freya LLM, the only model on staging and the one set in freya.py. The same for every team.



Rules
Enter solo or as a team of two.
You submit a builder. A hand-built phone agent on its own is not a valid entry.
The final phone agent must come out of the submitted commit with no manual edits.
Submit the trace of the builder run that made it. An entry without a trace is not ranked.
On the practice cases the phone agent may call only the tool API from the kit. In the final it calls only your own mock. A call to any other service fails the conversation.
Keep your mock running until the results are out.
Do not probe or load-test the platform. One Freya key per team.
You may fix bugs in your builder after the final case opens. Nothing from the final case may be written into it. A reviewer checks the commit for that.
All data is synthetic. Do not bring real customer data.
Prizes
Place	Prize
First	YC interview
Second	AirPods
Top three	Final interview with Freya
Prize pool	$3,000 in Freya credits


Rules
Enter solo or as a team of two.
You submit a builder. A hand-built phone agent on its own is not a valid entry.
The final phone agent must come out of the submitted commit with no manual edits.
Submit the trace of the builder run that made it. An entry without a trace is not ranked.
On the practice cases the phone agent may call only the tool API from the kit. In the final it calls only your own mock. A call to any other service fails the conversation.
Keep your mock running until the results are out.
Do not probe or load-test the platform. One Freya key per team.
You may fix bugs in your builder after the final case opens. Nothing from the final case may be written into it. A reviewer checks the commit for that.
All data is synthetic. Do not bring real customer data.
Prizes
Place	Prize
First	YC interview
Second	AirPods
Top three	Final interview with Freya
Prize pool	$3,000 in Freya credits