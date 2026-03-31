"""Visual Generator Agent - Generates complex visuals using Python/matplotlib."""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional

from artifactforge.coordinator import artifacts as schemas
from artifactforge.coordinator.contracts import (
    VISUAL_GENERATOR_CONTRACT,
    agent_contract,
)


VISUAL_GENERATOR_SYSTEM = """You are a Visual Generator - an expert at creating data visualizations with Python and matplotlib.

Your job is to generate Python code that creates charts and graphs for complex visualizations.

## Visual Types and matplotlib approaches
- bar_chart: plt.bar(), ax.barh()
- line_chart: plt.plot(), ax.plot()
- pie_chart: plt.pie()
- scatter_plot: plt.scatter()
- heatmap: sns.heatmap(), plt.imshow()
- statistical_chart: Multiple types combined

## Output Requirements
For each visual spec, generate Python code that:
1. Creates the figure with appropriate size
2. Uses the provided data_spec
3. Includes title, labels, legend
4. Saves to a file or returns SVG

Return JSON array with:
- visual_id: Matching the input spec
- visual_type: Type generated
- generated_code: The Python code (if complex)
- svg_output: SVG string (if Mermaid converted)
- image_path: Path to saved image (if generated)
- generation_method: "mermaid" or "python"
- notes: Any notes about generation"""


@agent_contract(VISUAL_GENERATOR_CONTRACT)
def run_visual_generator(
    visual_specs: list[schemas.VisualSpec],
    approved_reviews: Optional[list[dict]] = None,
) -> list[schemas.VisualGeneration]:
    """Generate visual assets from approved specs.

    Args:
        visual_specs: Approved visual specifications
        approved_reviews: Reviews that approved these visuals

    Returns:
        List of generated visuals
    """
    if not visual_specs:
        return []

    approved_ids = set()
    if approved_reviews:
        for review in approved_reviews:
            if review.get("is_appropriate"):
                approved_ids.add(review.get("visual_id"))

    results = []
    for spec in visual_specs:
        if approved_reviews and spec.get("visual_id") not in approved_ids:
            continue

        if spec.get("complexity") == "SIMPLE" and spec.get("mermaid_code"):
            result = _generate_mermaid(spec)
        else:
            result = _generate_python(spec)
        results.append(result)

    return results


def _generate_mermaid(spec: dict) -> schemas.VisualGeneration:
    mermaid_code = spec.get("mermaid_code", "")

    if not mermaid_code:
        return {
            "visual_id": spec.get("visual_id", ""),
            "visual_type": spec.get("visual_type", ""),
            "generated_code": None,
            "svg_output": None,
            "image_path": None,
            "generation_method": "mermaid",
            "notes": "No Mermaid code provided",
        }

    try:
        import mermaid

        svg_output = mermaid.render(mermaid_code)
        image_path = None  # SVG doesn't need separate image path

        return {
            "visual_id": spec.get("visual_id", ""),
            "visual_type": spec.get("visual_type", ""),
            "generated_code": None,
            "svg_output": svg_output,
            "image_path": None,
            "generation_method": "mermaid",
            "notes": f"Mermaid rendered successfully",
        }
    except Exception as e:
        return {
            "visual_id": spec.get("visual_id", ""),
            "visual_type": spec.get("visual_type", ""),
            "generated_code": None,
            "svg_output": None,
            "image_path": None,
            "generation_method": "mermaid",
            "notes": f"Mermaid rendering failed: {str(e)}",
        }


def _generate_python(spec: dict) -> schemas.VisualGeneration:
    visual_type = spec.get("visual_type", "bar_chart")
    data_spec = spec.get("data_spec", {})
    title = spec.get("title", "Chart")
    visual_id = spec.get("visual_id", "output")

    code = _build_matplotlib_code(visual_type, data_spec, title, visual_id)

    # Execute the generated Python code
    image_path, svg_output, execution_notes = _execute_matplotlib_code(code, visual_id)

    return {
        "visual_id": visual_id,
        "visual_type": visual_type,
        "generated_code": code,
        "svg_output": svg_output,
        "image_path": image_path,
        "generation_method": "python",
        "notes": execution_notes,
    }


def _build_matplotlib_code(
    visual_type: str, data_spec: dict, title: str, visual_id: str = "output"
) -> str:
    data = data_spec.get("data", {})
    labels = data_spec.get("labels", [])

    if visual_type == "bar_chart":
        values = data.get("values", [])
        return f"""import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

labels = {labels}
values = {values}

fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(labels, values)
ax.set_title('{title}')
ax.set_xlabel('Category')
ax.set_ylabel('Value')
plt.tight_layout()
plt.savefig('visual_{visual_id}.png', dpi=150)
plt.savefig('visual_{visual_id}.svg')
plt.close()
"""

    elif visual_type == "line_chart":
        x_values = data.get("x", [])
        y_values = data.get("y", [])
        return f"""import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

x = {x_values}
y = {y_values}

fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(x, y, marker='o')
ax.set_title('{title}')
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.grid(True)
plt.tight_layout()
plt.savefig('visual_{visual_id}.png', dpi=150)
plt.savefig('visual_{visual_id}.svg')
plt.close()
"""

    elif visual_type == "pie_chart":
        values = data.get("values", [])
        return f"""import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

labels = {labels}
values = {values}

fig, ax = plt.subplots(figsize=(8, 8))
ax.pie(values, labels=labels, autopct='%1.1f%%')
ax.set_title('{title}')
plt.tight_layout()
plt.savefig('visual_{visual_id}.png', dpi=150)
plt.savefig('visual_{visual_id}.svg')
plt.close()
"""

    elif visual_type == "scatter_plot":
        x_values = data.get("x", [])
        y_values = data.get("y", [])
        return f"""import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

x = {x_values}
y = {y_values}

fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(x, y, alpha=0.6)
ax.set_title('{title}')
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.grid(True)
plt.tight_layout()
plt.savefig('visual_{visual_id}.png', dpi=150)
plt.savefig('visual_{visual_id}.svg')
plt.close()
"""

    return f"""import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.set_title('{title}')
plt.savefig('visual_{visual_id}.png', dpi=150)
plt.savefig('visual_{visual_id}.svg')
plt.close()
"""


def _execute_matplotlib_code(
    code: str, visual_id: str
) -> tuple[Optional[str], Optional[str], str]:
    """Execute generated matplotlib code and save image files.

    Args:
        code: Python code to execute
        visual_id: Unique identifier for the visual

    Returns:
        Tuple of (image_path, svg_output, notes)
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        code_path = Path(tmpdir) / f"visual_{visual_id}.py"
        code_path.write_text(code)

        try:
            result = subprocess.run(
                ["python", str(code_path)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return (
                    None,
                    None,
                    f"Execution failed: {result.stderr}",
                )

            png_path = Path(tmpdir) / f"visual_{visual_id}.png"
            svg_path = Path(tmpdir) / f"visual_{visual_id}.svg"

            output_dir = Path("outputs/visuals")
            output_dir.mkdir(parents=True, exist_ok=True)

            final_image_path = None
            final_svg_path = None

            if png_path.exists():
                final_image_path = str(output_dir / f"visual_{visual_id}.png")
                shutil.copy(png_path, final_image_path)

            if svg_path.exists():
                final_svg_path = str(output_dir / f"visual_{visual_id}.svg")
                shutil.copy(svg_path, final_svg_path)

            svg_output = None
            if svg_path.exists():
                svg_output = svg_path.read_text()

            notes = f"Executed successfully. PNG: {'yes' if final_image_path else 'no'}, SVG: {'yes' if svg_output else 'no'}"

            return final_image_path, svg_output, notes

        except subprocess.TimeoutExpired:
            return None, None, "Execution timed out after 30 seconds"
        except Exception as e:
            return None, None, f"Execution error: {str(e)}"


def _call_llm(system: str, prompt: str) -> str:
    from artifactforge.agents.llm_gateway import call_llm_sync

    return call_llm_sync(
        system_prompt=system, user_prompt=prompt, agent_name="visual_generator"
    )


__all__ = ["run_visual_generator", "VISUAL_GENERATOR_CONTRACT"]
