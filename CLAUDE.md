# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

artifactory is a multi-agent AI pipeline that generates knowledge artifacts (reports, RFPs, blog posts, slide decks, commit reviews) from natural language descriptions. It uses a 13-node LangGraph state machine called MCRS (Multi-agent Content Reasoning System) with epistemic tracking and revision loops.

## Commands

```bash
# Install
pip install -e ".[dev]"

# Run the CLI
artifactforge generate "description" --type report --auto

# Tests
pytest                                          # all tests
pytest tests/e2e/ -m e2e -v                     # e2e integration tests
pytest tests/agents/test_analyst.py -v           # single file
pytest tests/agents/test_analyst.py::TestName::test_method -v  # single test

# Linting & formatting
black artifactforge tests
ruff check artifactforge tests --fix
mypy artifactforge                              # strict mode enabled

# Database
docker-compose up -d postgres
alembic upgrade head
alembic revision --autogenerate -m "description"
```

## Architecture

### MCRS Pipeline (13 nodes)

The pipeline flows through `artifactforge/coordinator/mcrs_graph.py`:

1. **Intent Architect** - parses user prompt into ExecutionBrief
2. **Research Lead** - maps information terrain into ResearchMap
3. **Evidence Ledger** - classifies claims as VERIFIED/DERIVED/SPECULATIVE into ClaimLedger
4. **Analyst** - produces AnalyticalBackbone (second-order analysis)
5. **Output Strategist** - designs ContentBlueprint (structure, narrative)
6. **Draft Writer** - generates full draft prose
7. **Adversarial Reviewer** - red-team review with issues/suggestions
8. **Verifier** - fact-checking and consistency validation
9. **Final Arbiter** - routes to: polish, revise_draft, revise_research, or end
10. **Polisher** - grammar, tone, final refinement
11. **Visual Designer** - designs visual specs (optional branch)
12. **Visual Reviewer** - reviews visual quality
13. **Visual Generator** - renders visuals via matplotlib/mermaid

Revision loops: max 3 revisions (Draft Writer <-> Reviewer), max 2 upstream repairs. The Final Arbiter uses repair_locus to target which upstream agent should fix an issue.

### Key Modules

- **`artifactforge/coordinator/`** - LangGraph state machine, MCRSState (TypedDict), agent contracts, artifact schemas, validation
- **`artifactforge/agents/`** - 13 agent implementations + `llm_gateway.py` (centralized LLM calls with cost/token tracking) + `llm_client.py` (provider abstraction)
- **`artifactforge/cli/`** - CLI entry point (`main.py`, argparse)
- **`artifactforge/tools/research/`** - Web search integrations (Tavily, Exa, Perplexity, FireCrawl, Context7)
- **`artifactforge/observability/`** - PipelineEvent system, trace_node decorator, metrics tracking
- **`artifactforge/db/`** - SQLAlchemy models, Alembic migrations

### Design Patterns

- **Agent Contract Pattern**: Each agent has an `AgentContract` (mission, inputs, outputs, forbidden behaviors, pass/fail criteria) registered via `@agent_contract()` decorator
- **LLM Gateway**: All LLM calls go through `llm_gateway.py` for unified cost/token tracking. Supports OpenRouter, Anthropic, and Ollama providers
- **Epistemic Classification**: Evidence Ledger tracks claim confidence (VERIFIED >0.8, DERIVED, SPECULATIVE) with source dependency chains
- **Repair Locus**: When downstream agents find issues, they mark which upstream agent should fix it, enabling targeted repairs without full reruns

### State & Configuration

- Pipeline state: `MCRSState` TypedDict in `coordinator/state.py`
- Intermediate artifacts: Pydantic schemas in `coordinator/artifacts.py`
- Settings: Pydantic Settings in `config.py`, loaded from `.env`
- Model registry: `MODEL_REGISTRY` dict in `agents/llm_gateway.py` (override defaults there)
- Checkpointing: LangGraph MemorySaver (PostgreSQL optional)

## Testing Patterns

- `tests/conftest.py` provides `EventCollector` fixture for capturing/asserting pipeline event sequences
- `tests/e2e/fixtures.py` provides mock research tools and minimal schema instances
- Tests mock external research APIs to avoid real API calls
- Markers: `@pytest.mark.e2e`, `@pytest.mark.slow`
- Note from napkin.md: importing `artifactforge.cli.main` reads `.env` which can break pytest collection if extra keys are present

## Environment

Requires Python 3.11+. Copy `.env.example` to `.env`. Needs at least one LLM provider configured (OPENAI_API_KEY for OpenRouter, ANTHROPIC_API_KEY, or OLLAMA_BASE_URL + OLLAMA_MODEL).
