# CloudGuard AI: The Decision Gate for AWS Operations
Built by Dineshraj Dhanapathy via AWSUGMDU (Agent Experience Hackathon)

Live demo: https://main.d2wslsaw56enrs.amplifyapp.com/
Code: https://github.com/dineshrajdhanapathyDD/CloudGuard-AI

## Hook

Imagine an AWS operations assistant that ensures every action is grounded, appropriate, and safe. CloudGuard AI is that assistant, leveraging Strands Decider 2B to judge AWS tool calls before they execute. This results in a reliable, fast, and secure AWS investigation tool.

## The Project

CloudGuard AI is designed for on-call engineers and SREs who need a quick and trustworthy assistant for AWS investigations. Key features include:

- Investigating EC2 issues through chat: instance details, CloudWatch metrics, alarms, and a written summary.
- Every tool call is gated before it runs: grounded read-only calls proceed, while ungrounded or inappropriate calls are blocked, and ambiguous ones ask for clarification.
- A deterministic, fail-closed safety policy that the generative model cannot override: destructive or unknown tools, malformed arguments, or an unavailable decider never execute.
- A live decision panel in the demo UI showing the three Decider answers, the confidence, the latency, the policy outcome, and the full audit trace.
- Deployed on Amazon Bedrock AgentCore Runtime.

< FIGURE 1 of 5: upload submission/article/img/architecture.png here >
Alt text: Architecture on AWS: the browser loads the React dashboard from Amplify and calls an API Gateway HTTP API, which proxies to a Lambda that invokes the Bedrock AgentCore runtime; the Strands agent uses Amazon Bedrock Nova Pro for the reply and Strands Decider 2B to gate every tool call, with a fail-closed policy returning proceed, clarify or deny

## How I Built It

The architecture of CloudGuard AI consists of Strands Agents, various tools, Amazon Bedrock for the generative part, and AgentCore Runtime. Strands Decider 2B is integrated to make critical decisions. The build process was spec-driven, utilizing Kiro for development.

The agent runs on Amazon Bedrock AgentCore Runtime. The public demo is fully serverless: the React dashboard is hosted on AWS Amplify, and it calls a public endpoint on Amazon API Gateway (HTTP API) that proxies to an AWS Lambda. The Lambda, scoped by a least-privilege IAM role that can only call InvokeAgentRuntime, invokes the deployed AgentCore agent. That backend is defined as CloudFormation and deploys with one command. The browser never holds AWS credentials and never talks to AgentCore directly; the Lambda is the thin, credential-holding translator.

## The Decision Handed to Strands Decider 2B

The decision model is crucial for ensuring that tool calls are grounded, appropriate, and safe. This decision needs a fast, calibrated model rather than another LLM call. The typed questions and options are:

```python
QUESTIONS = {
    "args_grounded": Decider.noul(
        "Does every argument value in the proposed tool call appear in the conversation above - stated by the user or returned by an earlier tool?",
        {"true": "each argument value (for example the instance id) is present verbatim in the user's messages or an earlier tool result",
         "false": "at least one argument value does not appear anywhere in the conversation; it was guessed or invented"}),
    "appropriate": Decider.noul(
        "Is this tool an appropriate response to the user's request?",
        {"true": "a read-only investigation (reading instance details, metrics or alarms), or a change the user explicitly asked for",
         "false": "a change or destructive action (restart, stop, terminate, delete) the user did not ask for"}),
    "needs_clarify": Decider.noul(
        "Does essential information have to be clarified with the user before this action can safely run?",
        {"true": "a required detail is missing or ambiguous (which instance? which environment?); ask before acting",
         "false": "everything needed to act is present and unambiguous"}),
}
```

## Measured

The performance of Strands Decider 2B is measured against the Bedrock LLM. Here are the results:

< FIGURE 2 of 5: upload submission/article/img/bench-accuracy.png here >
Alt text: Accuracy of Strands Decider 2B and the Bedrock LLM on the labelled cases

< FIGURE 3 of 5: upload submission/article/img/bench-latency.png here >
Alt text: Median latency per decision for both

< FIGURE 4 of 5: upload submission/article/img/bench-cost.png here >
Alt text: Cost per 1,000 decisions for both

< FIGURE 5 of 5: upload submission/article/img/bench-confidence.png here >
Alt text: Accuracy against the share of decisions answered without a human, as the confidence threshold moves

| Metric                | Strands Decider 2B     | us.amazon.nova-pro-v1:0 |
|-----------------------|------------------------|-------------------------|
| Accuracy              | 82.2%                  | 86.7%                   |
| Latency p50 per decision | 2910 ms               | 3081 ms                 |
| Latency p95           | 3391 ms                | 3703 ms                 |
| Cost per 1,000 decisions | $0.0350              | $0.4740                 |
| Answered alone at confidence >= 0.7 | 29%                | 100%                    |
| Accuracy when confident | 92.3%               | 86.7%                   |

At the median, the decider was 1.1x faster than the LLM.

On raw accuracy over the held-out split, Amazon Nova Pro is ahead by about five points (87 percent versus 82 percent). I am reporting that as it is, and I think the honest reading is still a win for the decider, for three reasons.

First, accuracy when confident is the number a guardrail actually lives by, and there the decider leads: 92.3 percent versus 87 percent. The gate does not have to answer every call. Below a 0.55 confidence floor it defers, asking the user or routing to a human instead of guessing. On the calls it is confident enough to act on alone, it is more accurate than the LLM. A guardrail that knows when to abstain beats one that is confidently wrong.

Second, cost is about 13.5 times lower: 0.035 dollars versus 0.474 dollars per 1,000 decisions. The gate runs on every single tool call, so this compounds. A fleet running millions of operations pays cents with the decider and dollars with an LLM for the exact same safety check.

Third, the sample is small and the gap is noise. The held-out split is 16 cases, so five points is a single case. On the tuning split the decider actually led, 90.7 percent to 86.1 percent. I report the held-out numbers and do not cherry-pick the split that flatters the decider.

The honest weak spots: on the deployed checkpoint, grounding confidence on clearly grounded calls sits close to the floor, and the summarize and list-all-alarms cases are where the decider most often disagrees with my labels. The deterministic policy is fail-closed around all of this, so a miss never runs an unsafe action; it produces a clarify or a deny. Next steps are sharper option wording on the two weak questions (tuned only on the tune split), more labelled cases to cut the noise, and evaluating the newer Qwen3.5 decider checkpoint.

## The Reusable Decision Pattern

The decision pattern is located in the repo under `decision_patterns/guardrail_gate/` with its own README and tests. To reuse it:

1. List your irreversible/destructive tools in `DESTRUCTIVE_TOOLS` and the tools the agent is allowed to use in `ALLOWED_TOOLS`.
2. Reword the three questions for your domain.
3. Keep the facts code already knows (permission, risk, structural validation) in `policy.py`.
4. Tune thresholds with `./kit bench` and record the chosen values in `policy.py`.

## What I Learned / What's Next

Building CloudGuard AI highlighted the importance of a robust decision-making process in ensuring the safety and reliability of AWS operations. Future improvements will focus on enhancing the accuracy and speed of the decision model, as well as expanding the range of supported AWS tools.

## Footer

Links to the repo, the video, Strands Decider and the tags.

Built by Dineshraj Dhanapathy via AWSUGMDU (Agent Experience Hackathon).
