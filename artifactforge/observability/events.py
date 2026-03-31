"""Pipeline event system for real-time monitoring and E2E testing."""

import asyncio
import json
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
from dataclasses import dataclass, field, asdict


class EventType(str, Enum):
    PIPELINE_START = "pipeline_start"
    PIPELINE_END = "pipeline_end"
    NODE_ENTRY = "node_entry"
    NODE_EXIT = "node_exit"
    NODE_ERROR = "node_error"
    RETRY = "retry"
    ROUTE = "route"
    STATUS = "status"
    LLM_CALL = "llm_call"
    VERIFICATION = "verification"


@dataclass
class PipelineEvent:
    event_type: EventType
    trace_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    node_name: Optional[str] = None
    duration_ms: Optional[int] = None
    success: bool = True
    error: Optional[str] = None
    error_type: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    route_target: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp.isoformat(),
            "node_name": self.node_name,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
            "error_type": self.error_type,
            "metadata": self.metadata,
            "route_target": self.route_target,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class PipelineEventEmitter:
    """Emits structured pipeline events for monitoring and testing."""

    def __init__(self):
        self._listeners: list[Callable[[PipelineEvent], None]] = []
        self._event_history: list[PipelineEvent] = []
        self._max_history = 1000

    def add_listener(self, callback: Callable[[PipelineEvent], None]) -> None:
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[PipelineEvent], None]) -> None:
        self._listeners.remove(callback)

    def emit(self, event: PipelineEvent) -> None:
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        for listener in self._listeners:
            try:
                listener(event)
            except Exception:
                pass

    def emit_node_entry(
        self, trace_id: str, node_name: str, metadata: Optional[dict] = None
    ) -> None:
        self.emit(
            PipelineEvent(
                event_type=EventType.NODE_ENTRY,
                trace_id=trace_id,
                node_name=node_name,
                metadata=metadata or {},
            )
        )

    def emit_node_exit(
        self,
        trace_id: str,
        node_name: str,
        duration_ms: int,
        success: bool = True,
        metadata: Optional[dict] = None,
    ) -> None:
        self.emit(
            PipelineEvent(
                event_type=EventType.NODE_EXIT,
                trace_id=trace_id,
                node_name=node_name,
                duration_ms=duration_ms,
                success=success,
                metadata=metadata or {},
            )
        )

    def emit_node_error(
        self,
        trace_id: str,
        node_name: str,
        error: str,
        error_type: str,
        duration_ms: int,
    ) -> None:
        self.emit(
            PipelineEvent(
                event_type=EventType.NODE_ERROR,
                trace_id=trace_id,
                node_name=node_name,
                duration_ms=duration_ms,
                success=False,
                error=error,
                error_type=error_type,
            )
        )

    def emit_retry(
        self, trace_id: str, node_name: str, attempt: int, max_attempts: int
    ) -> None:
        self.emit(
            PipelineEvent(
                event_type=EventType.RETRY,
                trace_id=trace_id,
                node_name=node_name,
                metadata={"attempt": attempt, "max_attempts": max_attempts},
            )
        )

    def emit_route(
        self,
        trace_id: str,
        from_node: str,
        to_node: str,
        reason: Optional[str] = None,
    ) -> None:
        self.emit(
            PipelineEvent(
                event_type=EventType.ROUTE,
                trace_id=trace_id,
                node_name=from_node,
                route_target=to_node,
                metadata={"reason": reason} if reason else {},
            )
        )

    def emit_status(
        self,
        trace_id: str,
        message: str,
        node_name: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        event_metadata = {"message": message}
        if metadata:
            event_metadata.update(metadata)

        self.emit(
            PipelineEvent(
                event_type=EventType.STATUS,
                trace_id=trace_id,
                node_name=node_name,
                metadata=event_metadata,
            )
        )

    def emit_pipeline_start(
        self, trace_id: str, user_prompt: str, output_type: str
    ) -> None:
        self.emit(
            PipelineEvent(
                event_type=EventType.PIPELINE_START,
                trace_id=trace_id,
                metadata={"user_prompt": user_prompt, "output_type": output_type},
            )
        )

    def emit_pipeline_end(
        self,
        trace_id: str,
        success: bool,
        final_stage: Optional[str] = None,
        total_duration_ms: Optional[int] = None,
    ) -> None:
        self.emit(
            PipelineEvent(
                event_type=EventType.PIPELINE_END,
                trace_id=trace_id,
                node_name=final_stage,
                duration_ms=total_duration_ms,
                success=success,
            )
        )

    def get_events(
        self,
        trace_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
    ) -> list[PipelineEvent]:
        events = self._event_history
        if trace_id:
            events = [e for e in events if e.trace_id == trace_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events

    def clear_history(self) -> None:
        self._event_history.clear()


_default_emitter: Optional[PipelineEventEmitter] = None


def get_event_emitter() -> PipelineEventEmitter:
    global _default_emitter
    if _default_emitter is None:
        _default_emitter = PipelineEventEmitter()
    return _default_emitter


class EventPrinter:
    """Listener that prints events to console with formatting."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def __call__(self, event: PipelineEvent) -> None:
        timestamp = event.timestamp.strftime("%H:%M:%S.%f")[:-3]

        if event.event_type == EventType.NODE_ENTRY:
            print(f"  [{timestamp}] 🔄 {event.node_name} started")
        elif event.event_type == EventType.NODE_EXIT:
            status = "✅" if event.success else "❌"
            duration = f"{event.duration_ms}ms" if event.duration_ms else ""
            print(f"  [{timestamp}] {status} {event.node_name} completed {duration}")
        elif event.event_type == EventType.NODE_ERROR:
            print(f"  [{timestamp}] ❌ {event.node_name} ERROR: {event.error}")
        elif event.event_type == EventType.RETRY:
            print(
                f"  [{timestamp}] 🔁 {event.node_name} retry {event.metadata.get('attempt')}/{event.metadata.get('max_attempts')}"
            )
        elif event.event_type == EventType.ROUTE:
            print(f"  [{timestamp}] ➡️  {event.node_name} → {event.route_target}")
        elif event.event_type == EventType.STATUS:
            icon = "💓" if event.metadata.get("kind") == "heartbeat" else "ℹ️"
            scope = f" {event.node_name}" if event.node_name else ""
            print(f"  [{timestamp}] {icon}{scope} {event.metadata.get('message', '')}")
        elif event.event_type == EventType.PIPELINE_START:
            print(
                f"\n[{timestamp}] 🚀 Pipeline started: {event.metadata.get('output_type')}"
            )
        elif event.event_type == EventType.PIPELINE_END:
            status = "✅" if event.success else "❌"
            print(
                f"  [{timestamp}] {status} Pipeline ended ({event.node_name or 'complete'})"
            )
        elif self.verbose:
            print(f"  [{timestamp}] {event.event_type.value}: {event.node_name}")


def enable_live_display(verbose: bool = False) -> None:
    emitter = get_event_emitter()
    emitter.add_listener(EventPrinter(verbose=verbose))


__all__ = [
    "PipelineEvent",
    "EventType",
    "PipelineEventEmitter",
    "get_event_emitter",
    "EventPrinter",
    "enable_live_display",
]
