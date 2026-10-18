# Evaluation

Two complementary, reproducible evaluations of CloudGuard AI's decision gate.

## 1. End-to-end guardrail outcomes — `run_evaluation.py`

Runs the **whole gate** (Strands Decider 2B's three answers + the deterministic fail-closed
policy) over labelled scenarios in `scenarios.json` and scores the actual
**PROCEED / CLARIFY / DENY** outcome against the expected one.

```bash
# Windows
.venv\Scripts\python.exe evaluation\run_evaluation.py              # mock decider (offline, reproducible)
.venv\Scripts\python.exe evaluation\run_evaluation.py --decider real   # real Strands Decider 2B
# macOS / Linux
.venv/bin/python evaluation/run_evaluation.py
```

It reports guardrail decision accuracy, **false-allow rate** (unsafe/ungrounded calls that wrongly
proceeded), **false-deny rate** (legitimate calls wrongly blocked), clarification rate, and decider
latency (p50/p95), and writes `evaluation/results.json`.

**Modes.** `mock` (default) uses a deterministic, rule-based stand-in for the model so the policy
logic is exercised with no server, no cost and perfect reproducibility — ideal for CI. It is
clearly labelled as mock in the output and the results file; it is **not** the real model and its
numbers are not reported as model accuracy. `real` uses the configured Strands Decider 2B (local
server or the hosted API, per `.env`) and records the model's actual answers and latency.

The four hackathon scenarios (grounded investigation, missing identifier, unsupported destructive
action, ambiguous remediation) are the first four cases in `scenarios.json`.

## 2. Decider vs. an LLM baseline — `./kit bench`

The kit's benchmark compares Strands Decider 2B against an Amazon Bedrock LLM answering the **same
typed questions** on `agent/eval_cases.jsonl` (32 labelled cases, 16 held out in the `test` split):
accuracy, latency (p50/p95), cost per 1,000 decisions, and low-confidence handling.

```bash
./kit bench --split tune      # inspect misses, tune question wording / thresholds
./kit bench --split test      # report THESE held-out numbers
```

Outputs land in `submission/bench/` (`results.json`, `results.md`, and four charts). Tune only on
the `tune` split and report the `test` split, so the numbers are honest.

## Honesty

Every reported number must come from a real run. The `mock` decider mode is for logic coverage and
is always labelled as such; headline accuracy, latency and cost for the submission come from a
`--decider real` run and from `./kit bench --split test` against the real model. Report weak spots
as they are.

Built by Dineshraj Dhanapathy via AWSUGMDU (Agent Experience Hackathon).
