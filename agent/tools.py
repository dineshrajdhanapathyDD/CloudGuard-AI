"""CloudGuard AI tools: a small, read-only AWS investigation toolkit.

All implementations here are SIMULATED so the demo, tests and benchmark run anywhere with no AWS
account and no live resources. Every result is explicitly stamped `"source": "simulated"` so the
UI and anyone reading a transcript can tell mock data from a real AWS call. Nothing here performs a
destructive operation, and no credentials are ever read or printed.

To use real read-only AWS data instead, set CLOUDGUARD_LIVE_AWS=1 and provide AWS credentials
through the standard provider chain (environment, shared config, or an IAM role). The live path
uses boto3 read-only describe/get calls only, scoped to the four tools below, and falls back to the
simulated sample when a resource is not found or credentials are missing - it never invents data.

Keep each tool's one-line docstring: the model reads it, and it becomes the option description for
tool-selection-style patterns.
"""

from __future__ import annotations

import os

from strands import tool

from decider_kit.data import load

# Clearly-labelled simulated fleet. Loaded from agent/data/ec2_instances.json so the data is
# deterministic and editable; a built-in fallback keeps the kit runnable before data is generated.
_FALLBACK_INSTANCES = {
    "i-1234567890abcdef0": {"instance_type": "m5.xlarge", "state": "running", "az": "us-east-1a",
                            "name": "web-prod-1", "launched": "2026-09-01", "environment": "production"},
    "i-0abc1111222233334": {"instance_type": "t3.medium", "state": "running", "az": "us-east-1b",
                           "name": "batch-worker-2", "launched": "2026-10-05", "environment": "staging"},
    "i-09f8e7d6c5b4a3210": {"instance_type": "c6g.2xlarge", "state": "stopped", "az": "us-east-1c",
                            "name": "analytics-1", "launched": "2026-08-20", "environment": "production"},
}


def _instances() -> dict:
    try:
        rows = load("ec2_instances")
        return {r["instance_id"]: {k: v for k, v in r.items() if k != "instance_id"} for r in rows}
    except FileNotFoundError:
        return dict(_FALLBACK_INSTANCES)


def _live() -> bool:
    return os.environ.get("CLOUDGUARD_LIVE_AWS") == "1"


@tool
def get_ec2_instance_details(instance_id: str) -> dict:
    """Describe one EC2 instance (type, state, AZ, tags). Read-only investigation."""
    iid = instance_id.strip()
    if _live():
        live = _live_instance_details(iid)
        if live is not None:
            return live
    inst = _instances().get(iid)
    if not inst:
        return {"error": f"no instance {iid} in the simulated fleet", "source": "simulated"}
    return {"instance_id": iid, "source": "simulated", **inst}


@tool
def get_ec2_metrics(instance_id: str, metric: str = "CPUUtilization", period_minutes: int = 60) -> dict:
    """Read a CloudWatch metric time series for an EC2 instance over a recent window. Read-only."""
    iid = instance_id.strip()
    if _live():
        live = _live_metrics(iid, metric, period_minutes)
        if live is not None:
            return live
    inst = _instances().get(iid)
    if not inst:
        return {"error": f"no instance {iid} in the simulated fleet", "source": "simulated"}
    # Deterministic pseudo-series so the demo is stable; clearly simulated.
    seed = sum(ord(c) for c in iid + metric)
    points = [round((seed * (i + 3)) % 97 + (12 if metric == "CPUUtilization" else 1), 1) for i in range(6)]
    return {"instance_id": iid, "metric": metric, "period_minutes": period_minutes,
            "unit": "Percent" if metric == "CPUUtilization" else "Count/Bytes",
            "datapoints": points, "latest": points[-1], "source": "simulated"}


@tool
def get_cloudwatch_alarms(instance_id: str = "") -> dict:
    """List CloudWatch alarms, optionally for one instance. Read-only."""
    iid = instance_id.strip()
    if _live():
        live = _live_alarms(iid)
        if live is not None:
            return live
    alarms = [
        {"name": "web-prod-1-cpu-high", "instance_id": "i-1234567890abcdef0", "metric": "CPUUtilization",
         "state": "ALARM", "threshold": 80},
        {"name": "analytics-1-status-check", "instance_id": "i-09f8e7d6c5b4a3210", "metric": "StatusCheckFailed",
         "state": "OK", "threshold": 1},
    ]
    if iid:
        alarms = [a for a in alarms if a["instance_id"] == iid]
    return {"instance_id": iid or "all", "alarms": alarms, "count": len(alarms), "source": "simulated"}


@tool
def summarize_investigation(instance_id: str, findings: str) -> dict:
    """Record a plain-language summary of an investigation's findings. Read-only."""
    return {"instance_id": instance_id.strip(), "summary": findings.strip(), "source": "simulated"}


# --- Optional live read-only AWS adapters (boto3), enabled only with CLOUDGUARD_LIVE_AWS=1 -------
# These use describe/get calls only. On any failure they return None so the caller falls back to the
# clearly-labelled simulated sample, and they never claim success for a call that did not run.

def _boto3_client(service: str):
    try:
        import boto3  # imported lazily so the kit runs without AWS libs configured
    except Exception:
        return None
    try:
        return boto3.client(service)  # region/credentials from the standard provider chain
    except Exception:
        return None


def _live_instance_details(instance_id: str):
    ec2 = _boto3_client("ec2")
    if ec2 is None:
        return None
    try:
        resp = ec2.describe_instances(InstanceIds=[instance_id])
        res = resp["Reservations"][0]["Instances"][0]
        tags = {t["Key"]: t["Value"] for t in res.get("Tags", [])}
        return {"instance_id": instance_id, "source": "aws",
                "instance_type": res.get("InstanceType"), "state": res.get("State", {}).get("Name"),
                "az": res.get("Placement", {}).get("AvailabilityZone"), "name": tags.get("Name"),
                "environment": tags.get("Environment")}
    except Exception:
        return None


def _live_metrics(instance_id: str, metric: str, period_minutes: int):
    cw = _boto3_client("cloudwatch")
    if cw is None:
        return None
    try:
        from datetime import datetime, timedelta, timezone
        end = datetime.now(timezone.utc)
        resp = cw.get_metric_statistics(
            Namespace="AWS/EC2", MetricName=metric,
            Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            StartTime=end - timedelta(minutes=period_minutes), EndTime=end,
            Period=300, Statistics=["Average"])
        pts = [round(d["Average"], 1) for d in sorted(resp.get("Datapoints", []), key=lambda d: d["Timestamp"])]
        if not pts:
            return None
        return {"instance_id": instance_id, "metric": metric, "period_minutes": period_minutes,
                "datapoints": pts, "latest": pts[-1], "source": "aws"}
    except Exception:
        return None


def _live_alarms(instance_id: str):
    cw = _boto3_client("cloudwatch")
    if cw is None:
        return None
    try:
        resp = cw.describe_alarms()
        alarms = []
        for a in resp.get("MetricAlarms", []):
            dims = {d["Name"]: d["Value"] for d in a.get("Dimensions", [])}
            if instance_id and dims.get("InstanceId") != instance_id:
                continue
            alarms.append({"name": a.get("AlarmName"), "instance_id": dims.get("InstanceId"),
                           "metric": a.get("MetricName"), "state": a.get("StateValue"),
                           "threshold": a.get("Threshold")})
        return {"instance_id": instance_id or "all", "alarms": alarms, "count": len(alarms), "source": "aws"}
    except Exception:
        return None


TOOLS = [get_ec2_instance_details, get_ec2_metrics, get_cloudwatch_alarms, summarize_investigation]
