from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import scripts.dashboard_server as dashboard
from app import agent as agent_module


def test_dashboard_data_uses_all_six_contract_panels(
    monkeypatch, tmp_path: Path
) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    timestamp = (now - timedelta(seconds=10)).isoformat().replace("+00:00", "Z")
    records = [
        {
            "ts": timestamp,
            "event": "request_received",
            "correlation_id": "req-12345678",
        },
        {
            "ts": timestamp,
            "event": "response_sent",
            "latency_ms": 1000,
            "ttft_ms": 100,
            "cost_usd": 0.01,
            "tokens_in": 20,
            "tokens_out": 30,
            "quality_score": 0.8,
            "tool_success": True,
        },
        {
            "ts": timestamp,
            "event": "request_received",
            "correlation_id": "req-87654321",
        },
        {
            "ts": timestamp,
            "event": "request_failed",
            "error_type": "RuntimeError",
            "tool_name": "retrieval",
            "tool_success": False,
        },
    ]
    log_path = tmp_path / "logs.jsonl"
    log_path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dashboard, "LOG_PATH", log_path)

    result = dashboard.compute_dashboard_data(now=now)
    panels = {panel["id"]: panel for panel in result["panels"]}

    assert set(panels) == {"latency", "traffic", "errors", "cost", "tokens", "quality"}
    assert panels["latency"]["values"][1]["value"] == 1000
    assert panels["traffic"]["values"][0]["value"] == 2
    assert panels["errors"]["values"][0]["value"] == 50
    assert panels["errors"]["values"][2]["value"] == 50
    assert panels["cost"]["values"][0]["value"] == 0.01
    assert panels["tokens"]["values"][0]["value"] == 20
    assert panels["quality"]["values"][0]["value"] == 0.8


class _ManagedPrompt:
    version = 5

    def compile(self, **variables: str) -> str:
        return (
            f"Feature={variables['feature']}\n"
            f"Docs={variables['docs']}\n"
            f"Question={variables['message']}"
        )


class _Observation:
    def __init__(self, options: dict) -> None:
        self.options = options
        self.updates: list[dict] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False

    def update(self, **kwargs) -> None:
        self.updates.append(kwargs)


class _RecordingClient:
    def __init__(self) -> None:
        self.prompt = _ManagedPrompt()
        self.observations: list[_Observation] = []
        self.span_updates: list[dict] = []

    def get_prompt(self, name: str, **kwargs):
        return self.prompt

    def update_current_span(self, **kwargs) -> None:
        self.span_updates.append(kwargs)

    def start_as_current_observation(self, **kwargs):
        observation = _Observation(kwargs)
        self.observations.append(observation)
        return observation


def test_generation_observation_links_prompt_usage_cost_and_safe_previews(
    monkeypatch,
) -> None:
    monkeypatch.setenv("LANGFUSE_PROMPT_NAME", "day13-chat")
    monkeypatch.setenv("LANGFUSE_PROMPT_LABEL", "production")
    monkeypatch.setattr(agent_module, "tracing_enabled", lambda: True)
    client = _RecordingClient()
    monkeypatch.setattr(agent_module, "get_langfuse_client", lambda: client)
    monkeypatch.setattr(agent_module, "retrieve", lambda _message: ["Safe policy document"])

    propagated: list[dict] = []

    @contextmanager
    def record_attributes(**kwargs):
        propagated.append(kwargs)
        yield

    monkeypatch.setattr(agent_module, "propagate_attributes", record_attributes)
    agent = agent_module.LabAgent()
    agent_module.LabAgent.run.__wrapped__(
        agent,
        user_id="student-01",
        feature="qa",
        session_id="session-01",
        message="Email student@vinuni.edu.vn",
        correlation_id="req-12345678",
    )

    generation = client.observations[-1]
    assert generation.options["as_type"] == "generation"
    assert generation.options["model"] == agent.model
    assert generation.options["prompt"] is client.prompt
    assert generation.options["metadata"]["prompt_version"] == "5"
    assert "student@vinuni.edu.vn" not in generation.options["input"]["prompt_preview"]
    update = generation.updates[-1]
    assert update["usage_details"]["input_tokens"] > 0
    assert update["usage_details"]["output_tokens"] > 0
    assert update["cost_details"]["total"] >= 0
    assert "student@vinuni.edu.vn" not in str(update["output"])
    assert propagated[0]["metadata"]["correlation_id"] == "req-12345678"
