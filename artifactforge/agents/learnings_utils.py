"""Shared utility for injecting learnings context into agent prompts."""

from typing import Any, Optional


def build_learnings_section(learnings_context: Optional[dict[str, Any]]) -> str:
    """Build a prompt section from learnings context.

    Args:
        learnings_context: Dict with 'insights' list from persistence.fetch_learnings()

    Returns:
        Prompt section string, or empty string if no learnings.
    """
    if not learnings_context:
        return ""

    insights = learnings_context.get("insights", [])
    if not insights:
        return ""

    lines = ["\n## Learnings from Prior Runs"]
    lines.append("The following patterns were observed in previous pipeline runs. Use them to avoid known pitfalls:\n")

    for i, insight in enumerate(insights, 1):
        failure = insight.get("failure_mode", "Unknown issue")
        fix = insight.get("fix_applied")
        confidence = insight.get("confidence", 0.0)

        lines.append(f"{i}. **Issue** (confidence {confidence:.0%}): {failure}")
        if fix:
            lines.append(f"   **Fix**: {fix}")

    return "\n".join(lines)
