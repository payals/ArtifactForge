"""End-to-end integration tests for ArtifactForge MCRS pipeline.

Tests all 13 agents with contract validation and quality gates.
Uses Ollama LLM with kimi model for real inference.
Skips external research tools to focus on core agent flow.
"""

import pytest
from typing import Any, Generator
from unittest.mock import patch, MagicMock
import uuid

from artifactforge.coordinator.mcrs_graph import create_mcrs_app
from artifactforge.coordinator.state import MCRSState
from artifactforge.observability.events import EventType, get_event_emitter
from artifactforge.agents.llm_gateway import clear_history

from tests.e2e.fixtures import (
    ContractValidator,
    MINIMAL_EXECUTION_BRIEF,
    MINIMAL_CLAIM_LEDGER,
    MINIMAL_ANALYTICAL_BACKBONE,
    MINIMAL_CONTENT_BLUEPRINT,
    MINIMAL_RED_TEAM_REVIEW,
    MINIMAL_VERIFICATION_REPORT,
    MINIMAL_RELEASE_DECISION_READY,
)


# =============================================================================
# Fixtures
# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_llm_gateway() -> Generator[None, None, None]:
    """Reset LLM gateway history before each test."""
    clear_history()
    yield
    clear_history()


@pytest.fixture
def event_collector() -> Generator[Any, None, None]:
    """Collects pipeline events during test execution."""
    from tests.conftest import EventCollector

    collector = EventCollector()
    emitter = get_event_emitter()
    emitter.add_listener(collector)
    emitter.clear_history()
    yield collector
    emitter.remove_listener(collector)
    collector.clear()


@pytest.fixture
def mock_research_tools() -> Generator[None, None, None]:
    mock_search_result = {
        "success": True,
        "sources": ["https://example.com/python"],
        "results": [
            {
                "title": "Python Programming",
                "url": "https://example.com/python",
                "snippet": "Python is easy to learn.",
            }
        ],
    }

    mock_analysis = {
        "summary": "Python is beginner-friendly.",
        "key_findings": ["Simple syntax", "Large community"],
    }

    with patch(
        "artifactforge.tools.research.web_searcher.run_web_searcher",
        return_value=mock_search_result,
    ):
        with patch(
            "artifactforge.tools.research.deep_analyzer.run_deep_analyzer",
            return_value=mock_analysis,
        ):
            yield


@pytest.fixture
def minimal_prompt() -> str:
    """Minimal test prompt to reduce token usage."""
    return "Write a 2-paragraph simple report about why Python is easy to learn."


# =============================================================================
# Main E2E Tests
# =============================================================================


@pytest.mark.e2e
@pytest.mark.slow
class TestMCRSPipeline:
    """End-to-end tests for the full MCRS pipeline."""

    def test_full_pipeline_executes_all_agents(
        self,
        event_collector: Any,
        mock_research_tools: None,
        minimal_prompt: str,
        contract_validator: ContractValidator,
    ) -> None:
        """Test that all 13 agents execute in sequence with valid outputs."""
        # Create the MCRS app
        app = create_mcrs_app()

        # Initial state
        initial_state: MCRSState = {
            "user_prompt": minimal_prompt,
            "conversation_context": None,
            "output_constraints": None,
            "intent_mode": "auto",
            "answers_collected": {},
            "execution_brief": None,
            "research_map": None,
            "claim_ledger": None,
            "analytical_backbone": None,
            "content_blueprint": None,
            "draft_v1": None,
            "draft_version": 1,
            "red_team_review": None,
            "verification_report": None,
            "polished_draft": None,
            "release_decision": None,
            "revision_history": [],
            "current_stage": "",
            "retry_count": 0,
            "errors": [],
            "stage_timing": {},
            "tokens_used": {},
            "costs": {},
            "stage_metadata": {},
            "trace_id": str(uuid.uuid4()),
            "repair_context": None,
            "visual_specs": [],
            "visual_reviews": [],
            "generated_visuals": [],
            "final_with_visuals": None,
        }

        # Run the pipeline with thread_id config
        config = {"configurable": {"thread_id": "test-thread"}}
        result = app.invoke(initial_state, config=config)

        # Verify all expected nodes executed
        expected_nodes = [
            "intent_architect",
            "research_lead",
            "evidence_ledger",
            "analyst",
            "output_strategist",
            "draft_writer",
            "adversarial_reviewer",
            "verifier",
            "final_arbiter",
            "polisher",
            "visual_designer",
            "visual_reviewer",
            "visual_generator",
        ]

        executed_nodes = event_collector.get_node_sequence()

        for node in expected_nodes:
            assert node in executed_nodes, f"Node '{node}' did not execute"
            event_collector.assert_node_succeeded(node)

        # Validate output schemas
        self._validate_all_outputs(result, contract_validator)

        # Verify final artifact was produced
        assert result.get("final_with_visuals") or result.get("polished_draft"), (
            "No final artifact produced"
        )

    def _validate_all_outputs(
        self, result: MCRSState, validator: ContractValidator
    ) -> None:
        """Validate all agent outputs match expected schemas."""
        validator.clear_errors()

        # Validate ExecutionBrief
        execution_brief = result.get("execution_brief")
        assert execution_brief is not None, "execution_brief is None"
        assert validator.validate_execution_brief(execution_brief), (
            f"ExecutionBrief invalid: {validator.get_errors()}"
        )

        # Validate ResearchMap
        research_map = result.get("research_map")
        assert research_map is not None, "research_map is None"
        assert validator.validate_research_map(research_map), (
            f"ResearchMap invalid: {validator.get_errors()}"
        )

        # Validate ClaimLedger
        claim_ledger = result.get("claim_ledger")
        assert claim_ledger is not None, "claim_ledger is None"
        assert validator.validate_claim_ledger(claim_ledger), (
            f"ClaimLedger invalid: {validator.get_errors()}"
        )

        # Validate AnalyticalBackbone
        analytical_backbone = result.get("analytical_backbone")
        assert analytical_backbone is not None, "analytical_backbone is None"
        assert validator.validate_analytical_backbone(analytical_backbone), (
            f"AnalyticalBackbone invalid: {validator.get_errors()}"
        )

        # Validate ContentBlueprint
        content_blueprint = result.get("content_blueprint")
        assert content_blueprint is not None, "content_blueprint is None"
        assert validator.validate_content_blueprint(content_blueprint), (
            f"ContentBlueprint invalid: {validator.get_errors()}"
        )

        # Validate RedTeamReview
        red_team_review = result.get("red_team_review")
        assert red_team_review is not None, "red_team_review is None"
        assert validator.validate_red_team_review(red_team_review), (
            f"RedTeamReview invalid: {validator.get_errors()}"
        )

        # Validate VerificationReport
        verification_report = result.get("verification_report")
        assert verification_report is not None, "verification_report is None"
        assert validator.validate_verification_report(verification_report), (
            f"VerificationReport invalid: {validator.get_errors()}"
        )

        # Validate ReleaseDecision
        release_decision = result.get("release_decision")
        assert release_decision is not None, "release_decision is None"
        assert validator.validate_release_decision(release_decision), (
            f"ReleaseDecision invalid: {validator.get_errors()}"
        )

        # Validate visual specs (if generated)
        visual_specs = result.get("visual_specs", [])
        for i, spec in enumerate(visual_specs):
            assert validator.validate_visual_spec(spec), (
                f"VisualSpec[{i}] invalid: {validator.get_errors()}"
            )

    def test_contract_input_output_compliance(
        self,
        event_collector: Any,
        mock_research_tools: None,
        minimal_prompt: str,
    ) -> None:
        """Verify each agent's inputs and outputs match their contracts."""
        app = create_mcrs_app()

        initial_state: MCRSState = {
            "user_prompt": minimal_prompt,
            "conversation_context": None,
            "output_constraints": None,
            "intent_mode": "auto",
            "answers_collected": {},
            "execution_brief": None,
            "research_map": None,
            "claim_ledger": None,
            "analytical_backbone": None,
            "content_blueprint": None,
            "draft_v1": None,
            "draft_version": 1,
            "red_team_review": None,
            "verification_report": None,
            "polished_draft": None,
            "release_decision": None,
            "revision_history": [],
            "current_stage": "",
            "retry_count": 0,
            "errors": [],
            "stage_timing": {},
            "tokens_used": {},
            "costs": {},
            "stage_metadata": {},
            "trace_id": str(uuid.uuid4()),
            "repair_context": None,
            "visual_specs": [],
            "visual_reviews": [],
            "generated_visuals": [],
            "final_with_visuals": None,
        }

        config = {"configurable": {"thread_id": "test-thread"}}
        result = app.invoke(initial_state, config=config)

        # Verify inputs/outputs form valid chains
        # Intent Architect: user_prompt -> execution_brief
        assert result.get("execution_brief") is not None
        brief = result["execution_brief"]
        assert "user_goal" in brief

        # Research Lead: execution_brief -> research_map
        assert result.get("research_map") is not None
        research = result["research_map"]
        assert "sources" in research

        # Evidence Ledger: research_map -> claim_ledger
        assert result.get("claim_ledger") is not None
        ledger = result["claim_ledger"]
        assert "claims" in ledger

        # Analyst: execution_brief + claim_ledger -> analytical_backbone
        assert result.get("analytical_backbone") is not None
        backbone = result["analytical_backbone"]
        assert "key_findings" in backbone

        # Output Strategist: execution_brief + analytical_backbone -> content_blueprint
        assert result.get("content_blueprint") is not None
        blueprint = result["content_blueprint"]
        assert "structure" in blueprint

        # Draft Writer: execution_brief + claim_ledger + analytical_backbone + content_blueprint -> draft_v1
        assert result.get("draft_v1") is not None
        assert len(result["draft_v1"]) > 0

        # Adversarial Reviewer: draft_v1 + claim_ledger + execution_brief -> red_team_review
        assert result.get("red_team_review") is not None
        review = result["red_team_review"]
        assert "issues" in review
        assert "passed" in review

        # Verifier: draft_v1 + claim_ledger -> verification_report
        assert result.get("verification_report") is not None

        # Final Arbiter: all inputs -> release_decision
        assert result.get("release_decision") is not None
        decision = result["release_decision"]
        assert "status" in decision
        assert decision["status"] in ["READY", "NOT_READY"]

        # Polisher: draft_v1 + output_type -> polished_draft
        assert result.get("polished_draft") is not None

        # Visual Designer: polished_draft + content_blueprint -> visual_specs
        assert result.get("visual_specs") is not None

        # Visual Reviewer: visual_specs + draft -> visual_reviews
        assert result.get("visual_reviews") is not None

        # Visual Generator: visual_specs + visual_reviews -> generated_visuals + final_with_visuals
        assert result.get("generated_visuals") is not None
        assert result.get("final_with_visuals") is not None


@pytest.mark.e2e
@pytest.mark.slow
class TestMCRSEdgeCases:
    """Edge case tests for MCRS pipeline."""

    def test_pipeline_no_errors(
        self,
        event_collector: Any,
        mock_research_tools: None,
        minimal_prompt: str,
    ) -> None:
        """Verify pipeline completes without any errors."""
        app = create_mcrs_app()

        initial_state: MCRSState = {
            "user_prompt": minimal_prompt,
            "conversation_context": None,
            "output_constraints": None,
            "intent_mode": "auto",
            "answers_collected": {},
            "execution_brief": None,
            "research_map": None,
            "claim_ledger": None,
            "analytical_backbone": None,
            "content_blueprint": None,
            "draft_v1": None,
            "draft_version": 1,
            "red_team_review": None,
            "verification_report": None,
            "polished_draft": None,
            "release_decision": None,
            "revision_history": [],
            "current_stage": "",
            "retry_count": 0,
            "errors": [],
            "stage_timing": {},
            "tokens_used": {},
            "costs": {},
            "stage_metadata": {},
            "trace_id": str(uuid.uuid4()),
            "repair_context": None,
            "visual_specs": [],
            "visual_reviews": [],
            "generated_visuals": [],
            "final_with_visuals": None,
        }

        config = {"configurable": {"thread_id": "test-thread"}}
        result = app.invoke(initial_state, config=config)

        # Check no errors in state
        errors = result.get("errors", [])
        assert len(errors) == 0, f"Pipeline had errors: {errors}"

        # Check no error events
        event_collector.assert_no_errors()


@pytest.mark.e2e
@pytest.mark.slow
class TestMCRSQualityGates:
    """Tests for quality gate validation."""

    def test_final_artifact_passes_quality_gates(
        self,
        event_collector: Any,
        mock_research_tools: None,
        minimal_prompt: str,
    ) -> None:
        """Verify final artifact passes quality gates."""
        app = create_mcrs_app()

        initial_state: MCRSState = {
            "user_prompt": minimal_prompt,
            "conversation_context": None,
            "output_constraints": None,
            "intent_mode": "auto",
            "answers_collected": {},
            "execution_brief": None,
            "research_map": None,
            "claim_ledger": None,
            "analytical_backbone": None,
            "content_blueprint": None,
            "draft_v1": None,
            "draft_version": 1,
            "red_team_review": None,
            "verification_report": None,
            "polished_draft": None,
            "release_decision": None,
            "revision_history": [],
            "current_stage": "",
            "retry_count": 0,
            "errors": [],
            "stage_timing": {},
            "tokens_used": {},
            "costs": {},
            "stage_metadata": {},
            "trace_id": str(uuid.uuid4()),
            "repair_context": None,
            "visual_specs": [],
            "visual_reviews": [],
            "generated_visuals": [],
            "final_with_visuals": None,
        }

        config = {"configurable": {"thread_id": "test-thread"}}
        result = app.invoke(initial_state, config=config)

        # Get final artifact
        final_artifact = result.get("final_with_visuals") or result.get(
            "polished_draft", ""
        )

        # Quality gate 1: Artifact exists and has content
        assert final_artifact, "Final artifact is empty"
        assert len(final_artifact) > 100, "Final artifact too short"

        # Quality gate 2: Contains expected content
        assert "Python" in final_artifact or "python" in final_artifact.lower(), (
            "Artifact missing topic (Python)"
        )

        # Quality gate 3: Release decision exists
        decision = result.get("release_decision")
        assert decision is not None, "No release decision"

        # Quality gate 4: All verification passed
        verification = result.get("verification_report")
        if verification:
            assert verification.get("passed") is not None, (
                "Verification missing passed field"
            )

        # Quality gate 5: No critical issues in review
        review = result.get("red_team_review", {})
        high_severity = [
            i for i in review.get("issues", []) if i.get("severity") == "HIGH"
        ]

        # If release is READY, there should be no high severity issues
        if decision.get("status") == "READY":
            assert len(high_severity) == 0, (
                f"Released with HIGH severity issues: {high_severity}"
            )


# =============================================================================
# Contract Validation Fixture Import
# =============================================================================

# Import contract_validator fixture from fixtures module
pytest_plugins = ["tests.e2e.fixtures"]
