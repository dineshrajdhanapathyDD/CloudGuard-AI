# Use case

- **Pitch:** CloudGuard AI is an AWS operations assistant with a decision gate: before it runs any
  AWS investigation tool, Strands Decider 2B judges whether the call is grounded, appropriate and
  safe, so the agent never acts on invented instance ids or runs an action nobody asked for.
- **Who it is for:** on-call engineers and SREs who want a fast assistant for AWS investigations
  without the risk that an eager agent fabricates arguments or reaches for a destructive action.
- **Features:**
  - investigate EC2 issues through chat: instance details, CloudWatch metrics, alarms, and a
    written summary;
  - every tool call is gated before it runs - grounded read-only calls proceed, ungrounded or
    inappropriate calls are blocked, ambiguous ones ask for clarification;
  - a deterministic, fail-closed safety policy that the generative model cannot override: a
    destructive or unknown tool, malformed arguments, or an unavailable decider never execute;
  - a live decision panel in the demo UI showing the three Decider answers, the confidence, the
    latency, the policy outcome, and the full audit trace;
  - deployed on Amazon Bedrock AgentCore Runtime.
- **The decision handed to Strands Decider 2B:** before an AWS tool call, are its arguments
  grounded in what the user said, is the call appropriate for the request, and is essential
  information missing? (`#guardrails`)
- **Why a decision model:** grounding, appropriateness and "is something missing" are judgements
  over the conversation's language - exactly what an `if` cannot decide. The exact facts (is the
  tool allowed? is it destructive? does the instance id parse?) stay in code and feed the policy.
- **Amazon Bedrock:** the conversation, the tool use, and the human-readable explanation (Amazon
  Nova Pro by default).

Built by Dineshraj Dhanapathy via AWSUGMDU (Agent Experience Hackathon).
