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


class _FakeMetricsCollector:
    def __init__(self) -> None:
        self.recorded = []
        self._pool = object()

    async def record_stage(self, metrics) -> None:
        self.recorded.append(metrics)


@pytest.mark.asyncio
async def test_trace_node_records_stage_metrics(monkeypatch) -> None:
    collector = _FakeMetricsCollector()
    emitter = _FakeEmitter()

    monkeypatch.setattr(middleware, "get_event_emitter", lambda: emitter)
    monkeypatch.setattr(
        "artifactforge.observability.metrics.get_metrics_collector", lambda: collector
    )

    @middleware.trace_node("draft_writer")
    def decorated(state: dict[str, object]) -> dict[str, object]:
        return {"draft_v1": "full draft"}

    result = decorated(
        {
            "trace_id": "trace-123",
            "errors": [],
            "stage_timing": {},
            "stage_metadata": {},
            "tokens_used": {},
            "costs": {},
        }
    )

    await asyncio.sleep(0)

    assert result["current_stage"] == "draft_writer"
    assert len(collector.recorded) == 1
    metrics = collector.recorded[0]
    assert metrics.trace_id == "trace-123"
    assert metrics.node_name == "draft_writer"
    assert metrics.success is True
    assert emitter.status_events[0][2] == "Starting node execution"
    assert emitter.status_events[-1][2].startswith("Completed in")


@pytest.mark.asyncio
async def test_trace_node_emits_heartbeat_and_sets_trace_context(monkeypatch) -> None:
    collector = _FakeMetricsCollector()
    emitter = _FakeEmitter()

    monkeypatch.setattr(middleware, "STATUS_UPDATE_INTERVAL", 0.01)
    monkeypatch.setattr(middleware, "get_event_emitter", lambda: emitter)
    monkeypatch.setattr(
        "artifactforge.observability.metrics.get_metrics_collector", lambda: collector
    )

    @middleware.trace_node("research_lead")
    def decorated(state: dict[str, object]) -> dict[str, object]:
        import time

        time.sleep(0.03)
        return {"research_map": {"sources": []}}

    result = decorated(
        {
            "trace_id": "trace-heartbeat",
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
