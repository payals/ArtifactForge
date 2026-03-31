import asyncio

import pytest

from artifactforge.observability import middleware


class _FakeEmitter:
    def __init__(self) -> None:
        self.status_events: list[tuple[str, str | None, str, dict]] = []

    def emit_node_entry(self, trace_id: str, node_name: str, metadata: dict) -> None:
        return None

    def emit_node_exit(
        self,
        trace_id: str,
        node_name: str,
        duration_ms: int,
        success: bool,
        metadata: dict,
    ) -> None:
        return None

    def emit_node_error(
        self,
        trace_id: str,
        node_name: str,
        error: str,
        error_type: str,
        duration_ms: int,
    ) -> None:
        return None

    def emit_status(
        self,
        trace_id: str,
        message: str,
        node_name: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        self.status_events.append((trace_id, node_name, message, metadata or {}))


class _FakePersistence:
    def __init__(self) -> None:
        self.recorded_nodes: list[dict] = []
        self.enabled = True

    def record_node(self, **kwargs) -> None:
        self.recorded_nodes.append(kwargs)

    def record_evaluation(self, **kwargs) -> None:
        pass

    def record_quality_gate(self, **kwargs) -> None:
        pass


@pytest.mark.asyncio
async def test_trace_node_records_stage_metrics(monkeypatch) -> None:
    fake_persistence = _FakePersistence()
    emitter = _FakeEmitter()

    monkeypatch.setattr(middleware, "get_event_emitter", lambda: emitter)
    monkeypatch.setattr(
        "artifactforge.db.persistence.get_persistence", lambda: fake_persistence
    )

    @middleware.trace_node("draft_writer")
    def decorated(state: dict[str, object]) -> dict[str, object]:
        return {"draft_v1": "full draft"}

    artifact_id = "00000000-0000-0000-0000-000000000001"
    result = decorated(
        {
            "trace_id": "trace-123",
            "artifact_id": artifact_id,
            "errors": [],
            "stage_timing": {},
            "stage_metadata": {},
            "tokens_used": {},
            "costs": {},
        }
    )

    assert result["current_stage"] == "draft_writer"
    assert len(fake_persistence.recorded_nodes) == 1
    node_record = fake_persistence.recorded_nodes[0]
    assert node_record["artifact_id"] == artifact_id
    assert node_record["node_name"] == "draft_writer"
    assert node_record["success"] is True
    assert emitter.status_events[0][2] == "Starting node execution"
    assert emitter.status_events[-1][2].startswith("Completed in")


@pytest.mark.asyncio
async def test_trace_node_emits_heartbeat_and_sets_trace_context(monkeypatch) -> None:
    fake_persistence = _FakePersistence()
    emitter = _FakeEmitter()

    monkeypatch.setattr(middleware, "STATUS_UPDATE_INTERVAL", 0.01)
    monkeypatch.setattr(middleware, "get_event_emitter", lambda: emitter)
    monkeypatch.setattr(
        "artifactforge.db.persistence.get_persistence", lambda: fake_persistence
    )

    @middleware.trace_node("research_lead")
    def decorated(state: dict[str, object]) -> dict[str, object]:
        import time

        time.sleep(0.03)
        return {"research_map": {"sources": []}}

    result = decorated(
        {
            "trace_id": "trace-heartbeat",
            "artifact_id": "00000000-0000-0000-0000-000000000002",
            "errors": [],
            "stage_timing": {},
            "stage_metadata": {},
            "tokens_used": {},
            "costs": {},
        }
    )

    await asyncio.sleep(0)

    heartbeat_events = [
        event for event in emitter.status_events if event[3].get("kind") == "heartbeat"
    ]
    assert result["trace_id"] == "trace-heartbeat"
    assert middleware.get_trace_id() == "trace-heartbeat"
    assert heartbeat_events
