# CloudGuard AI frontend (React + Vite + Tailwind + TypeScript)

A polished operations dashboard for CloudGuard AI: a scenario launcher, overview stat cards, a
decision-mix donut, the conversation, and a live Strands Decider 2B decision panel with confidence
meters, the three typed-question probability bars, and an expandable audit trace per decision.

This is a standalone single-page app. It talks to the CloudGuard demo server (FastAPI,
`demo/server.py`) over `/api/*`, so the kit's own one-command demo (`kit.cmd demo`, the plain
`demo/static/index.html`) keeps working unchanged - this is an additional, richer UI.

## Run it (dev)

Two terminals from the repo root:

```bash
# 1. the backend API (talks to the deployed AgentCore agent, or a local one)
#    for the deployed agent:
#    $env:AGENTCORE_ARN=(Get-Content submission\deployment.json | ConvertFrom-Json).runtime_arn
#    $env:DEMO_TARGET="agentcore"
.venv\Scripts\python.exe -m uvicorn demo.server:app --port 8501

# 2. the frontend (proxies /api -> 127.0.0.1:8501)
cd frontend
npm install
npm run dev        # http://localhost:5173
```

Point the proxy elsewhere with `CLOUDGUARD_API=http://host:port npm run dev`.

## Build (production)

```bash
cd frontend
npm run build      # -> frontend/dist/
```

Serve `dist/` behind the same origin as the API (or any static host; set the API origin via the
proxy/rewrite of your host).

## Contract

- `GET /api/info` -> `{ agent, llm, bedrock_model, decider, target }`
- `POST /api/chat` `{ message, session_id }` -> `{ reply, decisions[], model_id, latency_ms, agent, eager, served_by? }`
- Each decision: `{ pattern, tool, args, verdict, reason, confidence, args_valid, decider_ok, decider_ms, args_grounded?, appropriate?, needs_clarify? }`

Built by Dineshraj Dhanapathy via AWSUGMDU (Agent Experience Hackathon).
