"""Metrics collection and storage for MCRS pipeline.

Metrics are now persisted via the SQLAlchemy-based persistence adapter
(artifactforge.db.persistence). This module provides the MetricsCollector
interface for structured logging of pipeline lifecycle events.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class StageMetrics(BaseModel):
    """Metrics for a single pipeline stage."""

    trace_id: str
    node_name: str
    start_time: datetime
    end_time: datetime
    duration_ms: int
    success: bool
    error: Optional[str] = None
    tokens_used: int = 0
    cost: float = 0.0


class PipelineRun(BaseModel):
    """Overall pipeline execution metrics."""

    trace_id: str
    user_prompt: str
    output_type: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_duration_ms: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    status: str = "running"
    final_stage: Optional[str] = None


class MetricsCollector:
    """Collects pipeline metrics. DB persistence is handled by db.persistence."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url

    async def initialize(self) -> None:
        """Initialize metrics collector (no-op, DB handled by persistence adapter)."""
        logger.info("Metrics collector initialized")

    async def start_pipeline(
        self, user_prompt: str, output_type: str, trace_id: str | None = None
    ) -> str:
        """Log start of pipeline execution."""
        if trace_id is None:
            trace_id = str(uuid.uuid4())

        logger.info("Pipeline started", trace_id=trace_id, output_type=output_type)
        return trace_id

    async def complete_pipeline(
        self,
        trace_id: str,
        status: str,
        final_stage: Optional[str] = None,
        total_tokens: int = 0,
        total_cost: float = 0.0,
    ) -> None:
        """Log completion of pipeline execution."""
        logger.info(
            "Pipeline completed",
            trace_id=trace_id,
            status=status,
            final_stage=final_stage,
            total_tokens=total_tokens,
            total_cost=total_cost,
        )

    async def close(self) -> None:
        """Close metrics collector (no-op)."""
        pass


_default_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    global _default_collector
    if _default_collector is None:
        from artifactforge.config import get_settings

        settings = get_settings()
        _default_collector = MetricsCollector(database_url=settings.database_url)
    return _default_collector


__all__ = ["MetricsCollector", "StageMetrics", "PipelineRun", "get_metrics_collector"]
