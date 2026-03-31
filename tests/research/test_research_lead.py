from artifactforge.agents.research_lead import run_research_lead


def test_run_research_lead_uses_deep_analysis(monkeypatch) -> None:
    deep_analysis_calls: list[tuple[list[str], str]] = []
    llm_prompts: list[str] = []

    monkeypatch.setattr(
        "artifactforge.agents.research_lead.run_web_searcher",
        lambda query, num_results=5: {
            "query": query,
            "sources": [
                f"https://example.com/{query.replace(' ', '-')}/1",
                f"https://example.com/{query.replace(' ', '-')}/2",
                f"https://example.com/{query.replace(' ', '-')}/3",
                f"https://example.com/{query.replace(' ', '-')}/4",
            ],
            "results": [
                {
                    "title": f"Result for {query}",
                    "url": f"https://example.com/{query.replace(' ', '-')}/1",
                    "snippet": "Relevant snippet",
                }
            ],
        },
    )
    monkeypatch.setattr(
        "artifactforge.agents.research_lead.run_deep_analyzer",
        lambda sources, query: (
            deep_analysis_calls.append((sources, query))
            or {
                "summary": f"Deep analysis for {query}",
                "key_findings": [f"Finding for {query}"],
            }
        ),
    )
    monkeypatch.setattr(
        "artifactforge.agents.research_lead._call_llm",
        lambda system, prompt: (
            llm_prompts.append(prompt)
            or """
        {
            "sources": [{"title": "Example", "url": "https://example.com", "relevance_score": 0.9, "key_findings": ["A"]}],
            "facts": ["Fact A"],
            "key_dimensions": ["Dimension A"],
            "competing_views": [],
            "data_gaps": [],
            "followup_questions": []
        }
        """
        ),
    )

    result = run_research_lead(
        {
            "user_goal": "AI agents",
            "output_type": "report",
            "must_answer_questions": ["What matters most?"],
            "likely_missing_dimensions": [],
            "open_questions_to_resolve": [],
        },
        existing_research={"facts": ["Earlier fact"]},
        repair_context={
            "source_node": "final_arbiter",
            "reason": "arbiter_repair_reroute",
        },
    )

    assert result["facts"] == ["Fact A"]
    assert deep_analysis_calls
    assert all(len(sources) == 3 for sources, _query in deep_analysis_calls)
    assert "## Existing Research to Build Upon" in llm_prompts[0]
    assert "## Repair Context" in llm_prompts[0]
