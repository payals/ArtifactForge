from artifactforge.agents.intent_architect import run_intent_architect


def test_run_intent_architect_preserves_clarification_metadata(monkeypatch) -> None:
    prompts: list[str] = []

    monkeypatch.setattr(
        "artifactforge.agents.intent_architect._call_llm",
        lambda system, prompt: (
            prompts.append(prompt)
            or '{"user_goal": "Need a report", "output_type": "report"}'
        ),
    )

    brief = run_intent_architect(
        user_prompt="Build a report",
        intent_mode="interactive",
        answers_collected={"q1": "Executive audience"},
        repair_context={
            "source_node": "final_arbiter",
            "reason": "arbiter_repair_reroute",
        },
    )

    assert brief["intent_mode"] == "interactive"
    assert brief["answers_collected"] == {"q1": "Executive audience"}
    assert "## Repair Context" in prompts[0]
