"""Persistence adapter — thin layer between MCRS pipeline and PostgreSQL.

All methods no-op when DATABASE_URL is not configured.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Confidence threshold for learnings injection
LEARNINGS_CONFIDENCE_THRESHOLD = 0.7
# Max learnings injected per agent per run
LEARNINGS_CAP_PER_AGENT = 5

# Map pipeline nodes to Execution.phase for grouping
_NODE_PHASE = {
    "intent_architect": "intent",
    "research_lead": "research",
    "evidence_ledger": "research",
    "analyst": "analysis",
    "output_strategist": "strategy",
    "draft_writer": "generation",
    "adversarial_reviewer": "review",
    "verifier": "review",
    "polisher": "generation",
    "final_arbiter": "review",
    "visual_designer": "visual",
    "visual_reviewer": "visual",
    "visual_generator": "visual",
}

# Nodes whose output should be stored as Evaluation records
_EVALUATION_NODES = {"adversarial_reviewer", "verifier", "final_arbiter"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_session():
    """Get a new SQLAlchemy session, or None if DB not configured."""
    from artifactforge.db.session import SessionLocal

    if SessionLocal is None:
        return None
    return SessionLocal()


class PipelinePersistence:
    """Manages all DB reads/writes for the MCRS pipeline."""

    def __init__(self) -> None:
        self._enabled = self._check_enabled()

    @staticmethod
    def _check_enabled() -> bool:
        from artifactforge.db.session import SessionLocal

        return SessionLocal is not None

    @property
    def enabled(self) -> bool:
        return self._enabled

    # ------------------------------------------------------------------
    # Pipeline lifecycle
    # ------------------------------------------------------------------

    def start_run(
        self,
        trace_id: str,
        user_prompt: str,
        output_type: str,
    ) -> Optional[str]:
        """Create an Artifact row at pipeline start. Returns artifact_id or None."""
        if not self._enabled:
            return None

        from artifactforge.db.models import Artifact

        session = _get_session()
        if session is None:
            return None

        try:
            artifact = Artifact(
                id=uuid.UUID(trace_id),
                type=output_type,
                user_description=user_prompt,
                status="running",
                created_at=_now(),
                updated_at=_now(),
                meta={"trace_id": trace_id},
            )
            session.add(artifact)
            session.commit()
            artifact_id = str(artifact.id)
            logger.info("Created artifact %s for trace %s", artifact_id, trace_id)
            return artifact_id
        except Exception as e:
            session.rollback()
            logger.error("Failed to create artifact: %s", e)
            return None
        finally:
            session.close()

    def complete_run(
        self,
        artifact_id: str,
        status: str,
        final_draft: Optional[str],
        stage_timing: dict[str, float],
        tokens_used: dict[str, int],
        costs: dict[str, float],
        release_decision: Optional[dict] = None,
        review_results: Optional[dict] = None,
        verification_report: Optional[dict] = None,
    ) -> None:
        """Update Artifact row and write ArtifactMetrics on pipeline completion."""
        if not self._enabled or not artifact_id:
            return

        from artifactforge.db.models import Artifact
        from artifactforge.db.models_metrics import ArtifactMetrics

        session = _get_session()
        if session is None:
            return

        try:
            artifact_uuid = uuid.UUID(artifact_id)

            # Update artifact
            artifact = session.get(Artifact, artifact_uuid)
            if artifact:
                artifact.status = status
                artifact.completed_at = _now()
                artifact.updated_at = _now()
                if final_draft:
                    artifact.final_artifact = {"content": final_draft}
                if review_results:
                    artifact.review_results = review_results
                if verification_report:
                    artifact.verification_status = (
                        "passed" if verification_report.get("passed") else "failed"
                    )
                    artifact.verification_errors = verification_report

            # Compute aggregate metrics
            total_duration = int(sum(stage_timing.values()) * 1000)
            total_tokens_in = sum(tokens_used.values())
            total_cost = sum(costs.values())

            research_nodes = {"research_lead", "evidence_ledger"}
            gen_nodes = {"draft_writer", "polisher"}
            review_nodes = {"adversarial_reviewer", "verifier", "final_arbiter"}

            metrics = ArtifactMetrics(
                artifact_id=artifact_uuid,
                total_duration_ms=total_duration,
                research_duration_ms=int(
                    sum(v * 1000 for k, v in stage_timing.items() if k in research_nodes)
                ),
                generate_duration_ms=int(
                    sum(v * 1000 for k, v in stage_timing.items() if k in gen_nodes)
                ),
                review_duration_ms=int(
                    sum(v * 1000 for k, v in stage_timing.items() if k in review_nodes)
                ),
                total_input_tokens=total_tokens_in,
                total_output_tokens=0,
                estimated_cost_cents=total_cost * 100,
                evaluation_score=(
                    release_decision.get("confidence")
                    if release_decision
                    else None
                ),
                num_retries=0,
                created_at=_now(),
            )
            session.add(metrics)
            session.commit()
            logger.info("Completed artifact %s with status=%s", artifact_id, status)
        except Exception as e:
            session.rollback()
            logger.error("Failed to complete artifact: %s", e)
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Per-node execution recording
    # ------------------------------------------------------------------

    def record_node(
        self,
        artifact_id: str,
        node_name: str,
        duration_ms: int,
        tokens: int,
        cost: float,
        success: bool,
        error: Optional[str] = None,
        output_summary: Optional[dict] = None,
    ) -> None:
        """Write an Execution row for a completed node."""
        if not self._enabled or not artifact_id:
            return

        from artifactforge.db.models_executions import Execution

        session = _get_session()
        if session is None:
            return

        try:
            execution = Execution(
                artifact_id=uuid.UUID(artifact_id),
                phase=_NODE_PHASE.get(node_name, "unknown"),
                step=node_name,
                started_at=_now(),
                completed_at=_now(),
                duration_ms=duration_ms,
                input_tokens=tokens,
                output_tokens=0,
                status="success" if success else "failure",
                error_message=error,
                output=output_summary,
                meta={},
            )
            session.add(execution)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error("Failed to record node %s: %s", node_name, e)
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Evaluation persistence
    # ------------------------------------------------------------------

    def record_evaluation(
        self,
        artifact_id: str,
        node_name: str,
        issues: list[dict],
        passed: bool,
        confidence: Optional[float] = None,
    ) -> None:
        """Write an Evaluation row for reviewer/verifier/arbiter output."""
        if not self._enabled or not artifact_id:
            return

        from artifactforge.db.models_quality import Evaluation

        session = _get_session()
        if session is None:
            return

        try:
            high_count = sum(1 for i in issues if i.get("severity") == "HIGH")
            medium_count = sum(1 for i in issues if i.get("severity") == "MEDIUM")

            evaluation = Evaluation(
                artifact_id=uuid.UUID(artifact_id),
                evaluation_type="agent_review",
                evaluator=node_name,
                issues=issues,
                passed=passed,
                confidence=confidence,
                overall_score=1.0 if passed else max(0.0, 1.0 - high_count * 0.3 - medium_count * 0.1),
                created_at=_now(),
            )
            session.add(evaluation)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error("Failed to record evaluation for %s: %s", node_name, e)
        finally:
            session.close()

    def record_quality_gate(
        self,
        artifact_id: str,
        gate_name: str,
        passed: bool,
        score: Optional[float] = None,
        details: Optional[dict] = None,
        attempt: int = 1,
    ) -> None:
        """Write a QualityGateResult row."""
        if not self._enabled or not artifact_id:
            return

        from artifactforge.db.models_quality import QualityGateResult

        session = _get_session()
        if session is None:
            return

        try:
            gate = QualityGateResult(
                artifact_id=uuid.UUID(artifact_id),
                gate_name=gate_name,
                passed=passed,
                score=score,
                details=details,
                attempt=attempt,
                created_at=_now(),
            )
            session.add(gate)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error("Failed to record quality gate %s: %s", gate_name, e)
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Learnings — extraction (write)
    # ------------------------------------------------------------------

    def extract_learnings(
        self,
        artifact_id: str,
        artifact_type: str,
        revision_history: list[dict],
        release_decision: Optional[dict],
        errors: list[str],
        red_team_review: Optional[dict] = None,
    ) -> int:
        """Extract learnings from a completed run and write to DB.

        Returns number of learnings created.
        """
        if not self._enabled or not artifact_id:
            return 0

        from artifactforge.db.models_learnings import Learnings

        session = _get_session()
        if session is None:
            return 0

        learnings_to_add: list[Learnings] = []

        try:
            artifact_uuid = uuid.UUID(artifact_id)

            # 1. Extract from revision history — each revision is a learning opportunity
            for rev in revision_history:
                if rev.get("trigger") and rev["trigger"] != "draft":
                    learnings_to_add.append(
                        Learnings(
                            artifact_type=artifact_type,
                            context=f"Revision triggered by {rev.get('trigger', 'unknown')}",
                            failure_mode=f"Required revision: {rev.get('changes_made', 'unspecified')}",
                            fix_applied=f"Issues addressed: {', '.join(rev.get('issues_addressed', []))}",
                            outcome="success",
                            confidence=0.6,
                            source="revision_history",
                            artifact_id=artifact_uuid,
                            created_at=_now(),
                        )
                    )

            # 2. Extract from errors
            for error_msg in errors:
                learnings_to_add.append(
                    Learnings(
                        artifact_type=artifact_type,
                        context=f"Pipeline error in {error_msg.split(':')[0] if ':' in error_msg else 'unknown'}",
                        failure_mode=error_msg,
                        outcome="failure",
                        confidence=0.8,
                        source="pipeline_error",
                        artifact_id=artifact_uuid,
                        created_at=_now(),
                    )
                )

            # 3. Extract from release decision
            if release_decision:
                for risk in release_decision.get("remaining_risks", []):
                    learnings_to_add.append(
                        Learnings(
                            artifact_type=artifact_type,
                            context="Remaining risk identified by final arbiter",
                            failure_mode=f"Unresolved risk: {risk}",
                            outcome="needs_investigation",
                            confidence=0.5,
                            source="release_decision",
                            artifact_id=artifact_uuid,
                            created_at=_now(),
                        )
                    )
                for gap in release_decision.get("known_gaps", []):
                    learnings_to_add.append(
                        Learnings(
                            artifact_type=artifact_type,
                            context="Known gap identified by final arbiter",
                            failure_mode=f"Known gap: {gap}",
                            outcome="needs_investigation",
                            confidence=0.5,
                            source="release_decision",
                            artifact_id=artifact_uuid,
                            created_at=_now(),
                        )
                    )

            # 4. Extract from red team review — recurring HIGH issues become learnings
            if red_team_review:
                for issue in red_team_review.get("issues", []):
                    if issue.get("severity") == "HIGH":
                        learnings_to_add.append(
                            Learnings(
                                artifact_type=artifact_type,
                                context=f"HIGH severity issue from adversarial reviewer in section: {issue.get('section', 'unknown')}",
                                failure_mode=f"{issue.get('problem_type', 'unknown')}: {issue.get('explanation', '')}",
                                fix_applied=issue.get("suggested_fix"),
                                outcome="success" if release_decision and release_decision.get("status") == "READY" else "needs_investigation",
                                confidence=0.7,
                                source="adversarial_review",
                                artifact_id=artifact_uuid,
                                created_at=_now(),
                            )
                        )

            # Write all learnings
            for learning in learnings_to_add:
                session.add(learning)
            session.commit()

            count = len(learnings_to_add)
            if count:
                logger.info("Extracted %d learnings from artifact %s", count, artifact_id)
            return count

        except Exception as e:
            session.rollback()
            logger.error("Failed to extract learnings: %s", e)
            return 0
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Learnings — injection (read)
    # ------------------------------------------------------------------

    def fetch_learnings(
        self,
        agent_name: str,
        artifact_type: str,
    ) -> Optional[dict[str, Any]]:
        """Fetch relevant learnings for an agent, filtered by confidence threshold and capped.

        Returns a dict suitable for prompt injection, or None if no learnings found.
        """
        if not self._enabled:
            return None

        from sqlalchemy import desc

        from artifactforge.db.models_learnings import Learnings

        session = _get_session()
        if session is None:
            return None

        try:
            # Query learnings relevant to this artifact type with confidence above threshold
            rows = (
                session.query(Learnings)
                .filter(
                    Learnings.artifact_type == artifact_type,
                    Learnings.confidence >= LEARNINGS_CONFIDENCE_THRESHOLD,
                )
                .order_by(desc(Learnings.confidence), desc(Learnings.created_at))
                .limit(LEARNINGS_CAP_PER_AGENT)
                .all()
            )

            if not rows:
                return None

            # Build learnings context dict for prompt injection
            insights = []
            for row in rows:
                insight = {
                    "failure_mode": row.failure_mode,
                    "fix_applied": row.fix_applied,
                    "confidence": float(row.confidence),
                    "source": row.source,
                }
                insights.append(insight)

            # Update times_applied counter
            for row in rows:
                row.times_applied = (row.times_applied or 0) + 1
            session.commit()

            return {
                "agent": agent_name,
                "artifact_type": artifact_type,
                "insights": insights,
            }

        except Exception as e:
            session.rollback()
            logger.error("Failed to fetch learnings for %s: %s", agent_name, e)
            return None
        finally:
            session.close()


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------

_persistence: Optional[PipelinePersistence] = None


def get_persistence() -> PipelinePersistence:
    """Get or create the singleton persistence adapter."""
    global _persistence
    if _persistence is None:
        _persistence = PipelinePersistence()
    return _persistence


__all__ = ["PipelinePersistence", "get_persistence"]
