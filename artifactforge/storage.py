"""Storage utilities for intermediate artifact outputs."""

import json
import shutil
from pathlib import Path
from typing import Any, Optional


def get_temp_dir(artifact_id: str, base_dir: Optional[Path] = None) -> Path:
    """Get or create a temp directory for an artifact's intermediate outputs.

    Args:
        artifact_id: Unique identifier for this pipeline run
        base_dir: Optional base directory (defaults to system temp)

    Returns:
        Path to the temp directory for this artifact
    """
    if base_dir is None:
        base_dir = Path(__file__).parent.parent / "temp"

    artifact_dir = base_dir / artifact_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return artifact_dir


def save_intermediate(
    artifact_id: str,
    stage: str,
    data: Any,
    base_dir: Optional[Path] = None,
) -> Path:
    """Save intermediate artifact output to temp storage.

    Args:
        artifact_id: Unique identifier for this pipeline run
        stage: Current pipeline stage name (e.g., "research_lead", "draft_writer")
        data: Data to save (will be JSON serialized)
        base_dir: Optional base directory

    Returns:
        Path where data was saved
    """
    temp_dir = get_temp_dir(artifact_id, base_dir)
    output_path = temp_dir / f"{stage}.json"

    # Serialize to JSON
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)

    return output_path


def load_intermediate(
    artifact_id: str,
    stage: str,
    base_dir: Optional[Path] = None,
) -> Optional[Any]:
    """Load intermediate artifact output from temp storage.

    Args:
        artifact_id: Unique identifier for this pipeline run
        stage: Pipeline stage name to load
        base_dir: Optional base directory

    Returns:
        Loaded data or None if not found
    """
    temp_dir = get_temp_dir(artifact_id, base_dir)
    input_path = temp_dir / f"{stage}.json"

    if not input_path.exists():
        return None

    with open(input_path, "r") as f:
        return json.load(f)


def list_stages(artifact_id: str, base_dir: Optional[Path] = None) -> list[str]:
    """List all saved stages for an artifact.

    Args:
        artifact_id: Unique identifier for this pipeline run
        base_dir: Optional base directory

    Returns:
        List of stage names that have saved data
    """
    temp_dir = get_temp_dir(artifact_id, base_dir)

    if not temp_dir.exists():
        return []

    return [p.stem for p in temp_dir.glob("*.json")]


def cleanup(artifact_id: str, base_dir: Optional[Path] = None) -> None:
    """Clean up temp storage for an artifact.

    Args:
        artifact_id: Unique identifier for this pipeline run
        base_dir: Optional base directory
    """
    temp_dir = get_temp_dir(artifact_id, base_dir)

    if temp_dir.exists():
        shutil.rmtree(temp_dir)


__all__ = [
    "get_temp_dir",
    "save_intermediate",
    "load_intermediate",
    "list_stages",
    "cleanup",
]
