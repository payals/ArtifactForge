"""Metrics collection and storage for MCRS pipeline."""

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
    """Collects and stores pipeline metrics in PostgreSQL."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url
        self._pool = None

    async def initialize(self) -> None:
        """Initialize database connection and create tables."""
        if not self.database_url:
            logger.warning("No database_url provided, metrics will not be persisted")
            return

        try:
            import asyncpg

            self._pool = await asyncpg.create_pool(self.database_url)
            await self._create_tables()
            logger.info("Metrics collector initialized with PostgreSQL")
        except ImportError:
            logger.warning("asyncpg not installed, metrics will not be persisted")
        except Exception as e:
            logger.error("Failed to initialize metrics collector", error=str(e))

    async def _create_tables(self) -> None:
        """Create metrics tables if they don't exist."""
        if not self._pool:
            return

        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    trace_id UUID PRIMARY KEY,
                    user_prompt TEXT NOT NULL,
                    output_type VARCHAR(50) NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    total_duration_ms BIGINT DEFAULT 0,
                    total_tokens BIGINT DEFAULT 0,
                    total_cost DECIMAL(10, 6) DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'running',
                    final_stage VARCHAR(50)
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS stage_metrics (
                    id SERIAL PRIMARY KEY,
                    trace_id UUID REFERENCES pipeline_runs(trace_id),
                    node_name VARCHAR(50) NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP NOT NULL,
                    duration_ms BIGINT NOT NULL,
                    success BOOLEAN NOT NULL,
                    error TEXT,
                    tokens_used BIGINT DEFAULT 0,
                    cost DECIMAL(10, 6) DEFAULT 0
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_stage_metrics_trace_id
                ON stage_metrics(trace_id)
            """)

    async def start_pipeline(
        self, user_prompt: str, output_type: str, trace_id: str | None = None
    ) -> str:
        """Record start of pipeline execution."""
        if trace_id is None:
            trace_id = str(uuid.uuid4())

        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        """INSERT INTO pipeline_runs
                           (trace_id, user_prompt, output_type, started_at, status)
                           VALUES ($1, $2, $3, $4, 'running')""",
                        trace_id,
                        user_prompt,
                        output_type,
                        datetime.utcnow(),
                    )
            except Exception as e:
                logger.error("Failed to record pipeline start", error=str(e))

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
        """Record completion of pipeline execution."""
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        """UPDATE pipeline_runs
                           SET completed_at = $1, status = $2, final_stage = $3,
                               total_tokens = $4, total_cost = $5
                           WHERE trace_id = $6""",
                        datetime.utcnow(),
                        status,
                        final_stage,
                        total_tokens,
                        total_cost,
                        trace_id,
                    )
            except Exception as e:
                logger.error("Failed to record pipeline complete", error=str(e))

        logger.info(
            "Pipeline completed",
            trace_id=trace_id,
            status=status,
            final_stage=final_stage,
            total_tokens=total_tokens,
            total_cost=total_cost,
        )

    async def record_stage(self, metrics: StageMetrics) -> None:
        """Record metrics for a pipeline stage."""
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        """INSERT INTO stage_metrics
                           (trace_id, node_name, start_time, end_time,
                            duration_ms, success, error, tokens_used, cost)
                           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
                        metrics.trace_id,
                        metrics.node_name,
                        metrics.start_time,
                        metrics.end_time,
                        metrics.duration_ms,
                        metrics.success,
                        metrics.error,
                        metrics.tokens_used,
                        metrics.cost,
                    )
            except Exception as e:
                logger.error("Failed to record stage metrics", error=str(e))

    async def close(self) -> None:
        """Close database connection."""
        if self._pool:
            await self._pool.close()


_default_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    global _default_collector
    if _default_collector is None:
        from artifactforge.config import get_settings

        settings = get_settings()
        _default_collector = MetricsCollector(database_url=settings.database_url)
    return _default_collector


__all__ = ["MetricsCollector", "StageMetrics", "PipelineRun", "get_metrics_collector"]
