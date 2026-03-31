"""Tests for LLM Gateway."""

import pytest
from artifactforge.agents.llm_gateway import (
    get_agent_temperature,
    AGENT_TEMPERATURES,
    OLLAMA_MODEL,
)


class TestFixedModel:
    def test_ollama_model_is_set(self):
        assert OLLAMA_MODEL == "kimi-k2.5:cloud"


class TestAgentTemperatures:
    def test_intent_architect_temperature(self):
        assert get_agent_temperature("intent_architect") == 0.1

    def test_evidence_ledger_temperature(self):
        assert get_agent_temperature("evidence_ledger") == 0.0

    def test_draft_writer_temperature(self):
        assert get_agent_temperature("draft_writer") == 0.4

    def test_default_temperature(self):
        assert get_agent_temperature("unknown_agent") == 0.7


class TestTemperatureRegistry:
    def test_all_expected_agents_have_temperatures(self):
        expected_agents = [
            "intent_architect",
            "research_lead",
            "evidence_ledger",
            "analyst",
            "output_strategist",
            "draft_writer",
            "adversarial_reviewer",
            "verifier",
            "polisher",
            "final_arbiter",
            "visual_designer",
            "visual_reviewer",
            "visual_generator",
        ]
        for agent in expected_agents:
            assert agent in AGENT_TEMPERATURES
