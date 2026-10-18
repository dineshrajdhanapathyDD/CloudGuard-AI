"""Self-contained CloudGuard API for AWS Lambda (CloudFormation-deployed, zip packaging).

This is a thin, dependency-light backend that gives the public frontend an HTTPS endpoint to chat
through. It does exactly what demo/server.py's AgentCoreClient does - call the deployed Amazon
Bedrock AgentCore runtime - but without importing the agent code or the Strands SDK, so the Lambda
zip stays small (fastapi + mangum + pydantic; boto3 is in the Lambda runtime).

Routes (match the frontend's contract in frontend/src/services/api.ts):
  GET  /api/info   -> { agent, llm, bedrock_model, decider, target }
  POST /api/chat   -> { reply, decisions[], model_id, latency_ms, agent, eager, served_by }
  POST /api/reset  -> { ok: true }

Environment (set by the CloudFormation template):
  AGENTCORE_ARN     the deployed runtime ARN (required)
  AWS_REGION        provided by Lambda automatically
  BEDROCK_MODEL_ID  shown in /api/info (default us.amazon.nova-pro-v1:0)
  DECIDER_MODE      shown in /api/info (default ugmdu)
  CORS_ORIGIN       allowed browser origin for the Amplify site (default * )
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Any

import boto3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum
from pydantic import BaseModel

AGENT_NAME = "CloudGuard AI: the decision gate for AWS operations"
REGION = os.environ.get("AWS_REGION", "us-east-1")
ARN = os.environ.get("AGENTCORE_ARN", "")
BEDROCK_MODEL = os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-pro-v1:0")
DECIDER_MODE = os.environ.get("DECIDER_MODE", "ugmdu")
CORS_ORIGIN = os.environ.get("CORS_ORIGIN", "*")

app = FastAPI(title="CloudGuard API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN] if CORS_ORIGIN != "*" else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_client = boto3.client("bedrock-agentcore", region_name=REGION)
_sessions: dict[str, str] = {}


class Turn(BaseModel):
    message: str
    session_id: str = "web"
    images: list[str] = []


@app.get("/api/info")
def info() -> dict[str, Any]:
    return {
        "agent": AGENT_NAME,
        "llm": f"Amazon Bedrock ({BEDROCK_MODEL})",
        "bedrock_model": BEDROCK_MODEL,
        "decider": DECIDER_MODE,
        "target": "agentcore",
    }


@app.post("/api/chat")
def chat(t: Turn) -> JSONResponse:
    if not ARN:
        return JSONResponse({"error": "AGENTCORE_ARN is not configured on the server"}, status_code=500)
    try:
        sid = _sessions.setdefault(t.session_id, f"web-{t.session_id}-{uuid.uuid4().hex}")
        payload = {"prompt": t.message, **({"images": t.images} if t.images else {})}
        r = _client.invoke_agent_runtime(
            agentRuntimeArn=ARN, runtimeSessionId=sid, payload=json.dumps(payload).encode()
        )
        body = r["response"].read() if hasattr(r["response"], "read") else r["response"]
        out = json.loads(body)
        out["served_by"] = "Amazon Bedrock AgentCore Runtime"
        return JSONResponse(out)
    except Exception as e:  # noqa: BLE001 - surfaced to the UI
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)


@app.post("/api/reset")
def reset() -> dict[str, bool]:
    _sessions.clear()
    return {"ok": True}


handler = Mangum(app, lifespan="off")
