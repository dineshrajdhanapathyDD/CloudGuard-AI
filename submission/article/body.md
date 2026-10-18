# CloudGuard AI: The Decision Gate for AWS Operations
Built by Dineshraj Dhanapathy via AWSUGMDU (Agent Experience Hackathon)

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
Alt text: Architecture: the user, the agent with its tools and decision, Amazon Bedrock and Strands Decider 2B

## How I Built It

The architecture of CloudGuard AI consists of Strands Agents, various tools, Amazon Bedrock for the generative part, and AgentCore Runtime. Strands Decider 2B is integrated to make critical decisions. The build process was spec-driven, utilizing Kiro for development.

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
