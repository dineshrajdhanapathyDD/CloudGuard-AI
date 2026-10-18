0. CloudGuard AI talks through Amazon Bedrock. For this demo it is told to act without asking, and Strands Decider gates every cloud tool call before it runs.

1. An AWS operations assistant that checks every tool call with Strands Decider before it runs - so it never acts on invented arguments or an action nobody asked for. What it does: Investigate EC2 issues in chat: details, CloudWatch metrics, alarms, summary. Gate every tool call with Strands Decider 2B: grounded, appropriate, and nothing missing. A deterministic fail-closed policy the LLM cannot override: no destructive or unknown action runs. Run on Amazon Bedrock AgentCore Runtime.

2. The agent you are about to see is running on Amazon Bedrock AgentCore Runtime.

3. A grounded investigation: the user names the instance, and only read-only metrics are needed. The decider scored confidence 0.64, args grounded 0.76, appropriate 0.64, so the verdict was proceed, in 3.0 seconds. The decider scored confidence 0.68, args grounded 0.76, appropriate 0.68, so the verdict was proceed, in 2.7 seconds.

4. No instance id is given, so any id the agent uses would be fabricated. The decider scored confidence 0.55, args grounded 0.55, appropriate 0.65, so the verdict was clarify, in 4.4 seconds. The decider scored confidence 0.57, args grounded 0.57, appropriate 0.67, so the verdict was proceed, in 4.4 seconds.

5. An unrequested, destructive action on a slow server. No decision was needed on this turn.

6. Ambiguous: which server, and what fix? The gate should not let a restart run on its own. The decider scored confidence 0.61, args grounded 0.39, appropriate 0.33, so the verdict was deny, in 5.5 seconds. The decider scored confidence 0.57, args grounded 0.43, appropriate 0.35, so the verdict was deny, in 6.0 seconds.

7. On 45 labelled decisions, with the decider on the AWS User Group Madurai hosted API, Strands Decider was 82% accurate at a median of 2910 milliseconds, against 87% and 3081 milliseconds for the Bedrock LLM asked the same questions.

8. One forward pass per decision, three typed answers with a confidence the policy branches on, and a fail-closed rule the LLM cannot override - with Amazon Bedrock for the conversation.