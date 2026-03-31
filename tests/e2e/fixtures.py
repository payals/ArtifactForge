"""E2E test fixtures for ArtifactForge MCRS pipeline.

Provides mock data for research tools and expected schema fixtures for contract validation.
"""

from typing import Any
import pytest

from artifactforge.coordinator import artifacts as schemas


# =============================================================================
# Mock Research Data
# =============================================================================

MOCK_SEARCH_SOURCES = [
    {
        "source_id": "SRC_001",
        "title": "Python Programming Overview",
        "url": "https://example.com/python-overview",
        "source_type": "official",
        "reliability": "HIGH",
        "notes": "Official Python documentation and language features",
        "publish_date": "2026-01-15",
    },
    {
        "source_id": "SRC_002",
        "title": "Benefits of Python for Beginners",
        "url": "https://example.com/python-benefits",
        "source_type": "reference",
        "reliability": "MEDIUM",
        "notes": "Educational resource on Python advantages",
        "publish_date": "2026-02-10",
    },
]

MOCK_SEARCH_RESULTS = [
    {
        "title": "Python Programming Overview",
        "url": "https://example.com/python-overview",
        "snippet": "Python is a high-level programming language known for readability.",
    },
    {
        "title": "Benefits of Python for Beginners",
        "url": "https://example.com/python-benefits",
        "snippet": "Python offers simple syntax and extensive libraries.",
    },
]

MOCK_RESEARCH_MAP: schemas.ResearchMap = {
    "sources": MOCK_SEARCH_SOURCES,
    "facts": [
        "Python is a high-level programming language",
        "Python has simple, readable syntax",
        "Python has extensive standard library",
    ],
    "key_dimensions": ["syntax", "libraries", "community", "performance"],
    "competing_views": [
        "Some prefer statically typed languages",
        "Performance concerns vs ease of use",
    ],
    "data_gaps": ["Latest version adoption statistics"],
    "followup_questions": ["What are the most popular Python frameworks?"],
}


# =============================================================================
# Expected Schema Fixtures
# =============================================================================

MINIMAL_EXECUTION_BRIEF: schemas.ExecutionBrief = {
    "user_goal": "Write about Python",
    "output_type": "simple_report",
    "audience": "beginners",
    "tone": "conversational",
    "must_answer_questions": ["What makes Python easy to learn?"],
    "constraints": ["Keep under 200 words"],
    "success_criteria": ["Clear explanation", "Beginner-friendly"],
    "likely_missing_dimensions": ["performance", "ecosystem"],
    "decision_required": False,
    "rigor_level": "LOW",
    "persuasion_level": "LOW",
    "open_questions_to_resolve": [],
    "intent_mode": "auto",
    "answers_collected": {},
}

MINIMAL_CLAIM_LEDGER: schemas.ClaimLedger = {
    "claims": [
        {
            "claim_id": "C001",
            "claim_text": "Python has readable syntax",
            "classification": "VERIFIED",
            "source_refs": ["SRC_001"],
            "confidence": 0.95,
            "importance": "HIGH",
            "dependent_on": [],
            "notes": "Widely accepted fact",
        },
        {
            "claim_id": "C002",
            "claim_text": "Python is popular for beginners",
            "classification": "DERIVED",
            "source_refs": ["SRC_002"],
            "confidence": 0.8,
            "importance": "MEDIUM",
            "dependent_on": ["C001"],
            "notes": "Based on beginner tutorials",
        },
    ],
    "summary": "Mostly verified claims about Python",
}

MINIMAL_ANALYTICAL_BACKBONE: schemas.AnalyticalBackbone = {
    "key_findings": ["Python excels at readability"],
    "primary_drivers": ["Simple syntax", "Large community"],
    "implications": ["Lower barrier to entry"],
    "risks": ["Slower execution than compiled languages"],
    "sensitivities": ["Performance needs may require other languages"],
    "counterarguments": ["Static typing advocates prefer other languages"],
    "recommendation_logic": [],
    "open_unknowns": ["Exact adoption rates"],
}

MINIMAL_CONTENT_BLUEPRINT: schemas.ContentBlueprint = {
    "structure": ["Introduction", "Key Benefits", "Conclusion"],
    "section_purposes": {
        "Introduction": "Hook the reader",
        "Key Benefits": "Present main points",
        "Conclusion": "Wrap up",
    },
    "narrative_flow": "Start with what Python is, then why it helps beginners",
    "visual_elements": [],
    "key_takeaways": ["Python is easy to learn", "Great for beginners"],
    "audience_guidance": ["Use simple examples"],
}

MINIMAL_RED_TEAM_REVIEW: schemas.RedTeamReview = {
    "issues": [],
    "overall_assessment": "Draft is acceptable for simple report",
    "passed": True,
}

MINIMAL_RED_TEAM_REVIEW_WITH_ISSUES: schemas.RedTeamReview = {
    "issues": [
        {
            "issue_id": "R001",
            "severity": "HIGH",
            "section": "Introduction",
            "problem_type": "unsupported_claim",
            "repair_locus": "draft_writer",
            "explanation": "Claim about performance needs source",
            "suggested_fix": "Add citation or rephrase",
        }
    ],
    "overall_assessment": "Needs revision for unsupported claim",
    "passed": False,
}

MINIMAL_VERIFICATION_REPORT: schemas.VerificationReport = {
    "items": [
        {
            "claim_id": "C001",
            "status": "SUPPORTED",
            "repair_locus": "draft_writer",
            "notes": "Claim is well-supported",
            "required_action": None,
        }
    ],
    "summary": "All claims verified",
    "passed": True,
}

MINIMAL_RELEASE_DECISION_READY: schemas.ReleaseDecision = {
    "status": "READY",
    "confidence": 0.9,
    "remaining_risks": [],
    "known_gaps": ["Performance data incomplete"],
    "notes": "Ready to release",
}

MINIMAL_RELEASE_DECISION_NOT_READY: schemas.ReleaseDecision = {
    "status": "NOT_READY",
    "confidence": 0.6,
    "remaining_risks": ["Unsupported claim"],
    "known_gaps": ["Needs verification"],
    "notes": "Requires revision",
}

MINIMAL_VISUAL_SPEC: schemas.VisualSpec = {
    "visual_id": "V001",
    "section_anchor": "## Key Benefits",
    "visual_type": "concept_diagram",
    "title": "Python Learning Curve",
    "description": "Shows how Python is easier than other languages",
    "data_spec": {"languages": ["Python", "C++", "Java"]},
    "complexity": "SIMPLE",
    "mermaid_code": "graph LR\nA[Start] --> B[Python]\nA --> C[C++]\nB --> D[Productive]\nC --> E[Complex]",
    "placeholder_position": "after paragraph 1",
}

MINIMAL_VISUAL_REVIEW: schemas.VisualReview = {
    "visual_id": "V001",
    "is_appropriate": True,
    "clarity_score": 0.9,
    "data_accuracy": 0.85,
    "placement_correct": True,
    "issues": [],
    "suggestions": ["Consider adding specific time estimates"],
}

MINIMAL_VISUAL_GENERATION: schemas.VisualGeneration = {
    "visual_id": "V001",
    "visual_type": "concept_diagram",
    "generated_code": None,
    "svg_output": "<svg>...</svg>",
    "image_path": None,
    "generation_method": "mermaid",
    "notes": "Generated successfully",
}


# =============================================================================
# Contract Validator
# =============================================================================


class ContractValidator:
    """Validates agent outputs against expected schemas."""

    def __init__(self):
        self.errors: list[str] = []

    def validate_execution_brief(self, output: Any) -> bool:
        """Validate ExecutionBrief output."""
        required_fields = [
            "user_goal",
            "output_type",
            "audience",
            "tone",
            "must_answer_questions",
            "success_criteria",
            "decision_required",
            "rigor_level",
            "persuasion_level",
            "intent_mode",
        ]
        return self._validate_required_fields(output, required_fields, "ExecutionBrief")

    def validate_research_map(self, output: Any) -> bool:
        """Validate ResearchMap output."""
        required_fields = ["sources", "facts", "key_dimensions"]
        return self._validate_required_fields(output, required_fields, "ResearchMap")

    def validate_claim_ledger(self, output: Any) -> bool:
        """Validate ClaimLedger output."""
        required_fields = ["claims", "summary"]
        if not self._validate_required_fields(output, required_fields, "ClaimLedger"):
            return False

        # Validate each claim has required fields
        claims = output.get("claims", [])
        claim_required = [
            "claim_id",
            "claim_text",
            "classification",
            "confidence",
            "importance",
        ]
        for i, claim in enumerate(claims):
            for field in claim_required:
                if field not in claim:
                    self.errors.append(f"ClaimLedger.claim[{i}] missing '{field}'")
                    return False
        return True

    def validate_analytical_backbone(self, output: Any) -> bool:
        """Validate AnalyticalBackbone output."""
        required_fields = [
            "key_findings",
            "primary_drivers",
            "risks",
            "counterarguments",
        ]
        return self._validate_required_fields(
            output, required_fields, "AnalyticalBackbone"
        )

    def validate_content_blueprint(self, output: Any) -> bool:
        """Validate ContentBlueprint output."""
        required_fields = [
            "structure",
            "section_purposes",
            "narrative_flow",
            "key_takeaways",
        ]
        return self._validate_required_fields(
            output, required_fields, "ContentBlueprint"
        )

    def validate_red_team_review(self, output: Any) -> bool:
        """Validate RedTeamReview output."""
        required_fields = ["issues", "overall_assessment", "passed"]
        if not self._validate_required_fields(output, required_fields, "RedTeamReview"):
            return False

        # Validate issue structure if present
        for i, issue in enumerate(output.get("issues", [])):
            issue_required = ["issue_id", "severity", "problem_type", "repair_locus"]
            for field in issue_required:
                if field not in issue:
                    self.errors.append(f"RedTeamReview.issue[{i}] missing '{field}'")
                    return False
        return True

    def validate_verification_report(self, output: Any) -> bool:
        """Validate VerificationReport output."""
        required_fields = ["items", "summary", "passed"]
        return self._validate_required_fields(
            output, required_fields, "VerificationReport"
        )

    def validate_release_decision(self, output: Any) -> bool:
        """Validate ReleaseDecision output."""
        required_fields = [
            "status",
            "confidence",
            "remaining_risks",
            "known_gaps",
            "notes",
        ]
        return self._validate_required_fields(
            output, required_fields, "ReleaseDecision"
        )

    def validate_visual_spec(self, output: Any) -> bool:
        """Validate VisualSpec output."""
        required_fields = [
            "visual_id",
            "section_anchor",
            "visual_type",
            "title",
            "description",
            "data_spec",
            "complexity",
            "placeholder_position",
        ]
        return self._validate_required_fields(output, required_fields, "VisualSpec")

    def validate_visual_review(self, output: Any) -> bool:
        """Validate VisualReview output."""
        required_fields = [
            "visual_id",
            "is_appropriate",
            "clarity_score",
            "data_accuracy",
            "placement_correct",
            "issues",
            "suggestions",
        ]
        return self._validate_required_fields(output, required_fields, "VisualReview")

    def _validate_required_fields(
        self, output: Any, required: list[str], schema_name: str
    ) -> bool:
        """Check that all required fields exist in output."""
        if not isinstance(output, dict):
            self.errors.append(
                f"{schema_name}: expected dict, got {type(output).__name__}"
            )
            return False

        for field in required:
            if field not in output:
                self.errors.append(f"{schema_name}: missing required field '{field}'")
                return False
        return True

    def get_errors(self) -> list[str]:
        """Get all validation errors."""
        return self.errors

    def clear_errors(self) -> None:
        """Clear validation errors."""
        self.errors = []


@pytest.fixture
def contract_validator() -> ContractValidator:
    """Provide a fresh contract validator."""
    return ContractValidator()


@pytest.fixture
def minimal_test_prompt() -> str:
    """Minimal test prompt to reduce token usage."""
    return "Write a 2-paragraph simple report about why Python is easy to learn for beginners."


@pytest.fixture
def mock_research_data() -> dict[str, Any]:
    """Provide mock research data."""
    return {
        "sources": MOCK_SEARCH_SOURCES,
        "results": MOCK_SEARCH_RESULTS,
        "research_map": MOCK_RESEARCH_MAP,
    }
