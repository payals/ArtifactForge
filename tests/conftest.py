"""Pytest fixtures for ArtifactForge E2E testing."""

import os

os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("OLLAMA_MODEL", "kimi-k2.5:cloud")

import pytest
from typing import Generator

from artifactforge.observability.events import (
    PipelineEventEmitter,
    PipelineEvent,
    EventType,
    get_event_emitter,
)


class EventCollector:
    """Captures pipeline events during test execution."""

    def __init__(self):
        self.events: list[PipelineEvent] = []

    def __call__(self, event: PipelineEvent) -> None:
        self.events.append(event)

    def clear(self) -> None:
        self.events.clear()

    def get_by_type(self, event_type: EventType) -> list[PipelineEvent]:
        return [e for e in self.events if e.event_type == event_type]

    def get_by_node(self, node_name: str) -> list[PipelineEvent]:
        return [e for e in self.events if e.node_name == node_name]

    def get_node_sequence(self) -> list[str]:
        sequence = []
        for e in self.events:
            if e.event_type == EventType.NODE_ENTRY:
                sequence.append(e.node_name)
        return sequence

    def assert_node_completed(self, node_name: str) -> None:
        entries = self.get_by_node(node_name)
        exits = [e for e in entries if e.event_type == EventType.NODE_EXIT]
        assert len(exits) > 0, f"Node {node_name} did not complete"

    def assert_node_succeeded(self, node_name: str) -> None:
        exits = [
            e
            for e in self.events
            if e.event_type == EventType.NODE_EXIT and e.node_name == node_name
        ]
        assert len(exits) > 0, f"Node {node_name} did not exit"
        assert exits[0].success, f"Node {node_name} failed: {exits[0].error}"

    def assert_node_failed(self, node_name: str) -> None:
        errors = [
            e
            for e in self.events
            if e.event_type == EventType.NODE_ERROR and e.node_name == node_name
        ]
        assert len(errors) > 0, f"Node {node_name} did not error"

    def assert_no_errors(self) -> None:
        errors = self.get_by_type(EventType.NODE_ERROR)
        assert len(errors) == 0, (
            f"Pipeline had {len(errors)} errors: {[e.error for e in errors]}"
        )

    def get_timing(self, node_name: str) -> int:
        exits = [
            e
            for e in self.events
            if e.event_type == EventType.NODE_EXIT and e.node_name == node_name
        ]
        if exits:
            return exits[0].duration_ms or 0
        return 0


@pytest.fixture
def event_collector() -> Generator[EventCollector, None, None]:
    collector = EventCollector()
    emitter = get_event_emitter()
    emitter.add_listener(collector)
    emitter.clear_history()
    yield collector
    emitter.remove_listener(collector)
    collector.clear()


@pytest.fixture
def fresh_emitter() -> Generator[PipelineEventEmitter, None, None]:
    emitter = get_event_emitter()
    emitter.clear_history()
    yield emitter
    emitter.clear_history()
