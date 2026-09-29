from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import httpx

from app import logging_config
from app.logging_config import scrub_event
from app.main import app
from app.pii import scrub_text


def test_scrub_additional_cccd_and_payment_card_examples() -> None:
    cccd = scrub_text("CCCD: 012345678901")
    card = scrub_text("Card: 4111-1111-1111-1111")

    assert "012345678901" not in cccd
    assert "REDACTED_CCCD" in cccd
    assert "4111-1111-1111-1111" not in card
    assert "REDACTED_CREDIT_CARD" in card


def test_scrub_event_redacts_payload_strings() -> None:
    event = {
        "event": "request_received",
        "payload": {"message_preview": "Contact student@vinuni.edu.vn"},
    }

    safe_event = scrub_event(None, "info", event)

    assert "student@vinuni.edu.vn" not in str(safe_event)
    assert "REDACTED_EMAIL" in str(safe_event)


def test_chat_generates_request_id_and_logs_context(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.post(
                "/chat",
                json={
                    "user_id": "student-01",
                    "session_id": "session-01",
                    "feature": "qa",
                    "message": "Email student@vinuni.edu.vn",
                },
            )

    response = asyncio.run(send_request())

    request_id = response.headers["x-request-id"]
    assert response.status_code == 200
    assert re.fullmatch(r"req-[0-9a-f]{8}", request_id)
    assert response.json()["correlation_id"] == request_id
    assert float(response.headers["x-response-time-ms"]) >= 0

    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    received = next(item for item in events if item["event"] == "request_received")
    assert received["correlation_id"] == request_id
    assert received["user_id_hash"]
    assert received["session_id"] == "session-01"
    assert received["feature"] == "qa"
    assert received["model"] == "claude-sonnet-4-5"
    assert received["env"]
    assert "student@vinuni.edu.vn" not in log_path.read_text(encoding="utf-8")


def test_chat_preserves_a_valid_request_id(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.post(
                "/chat",
                headers={"x-request-id": "req-abcd1234"},
                json={
                    "user_id": "student-02",
                    "session_id": "session-02",
                    "feature": "qa",
                    "message": "Explain observability",
                },
            )

    response = asyncio.run(send_request())

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-abcd1234"
    assert response.json()["correlation_id"] == "req-abcd1234"
