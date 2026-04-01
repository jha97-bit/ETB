"""Rubric library: load rubrics from YAML files."""

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

RUBRICS_DIR = Path(__file__).parent


def load_rubric(mode: str) -> dict[str, Any]:
    """Load rubric for given interview mode (behavioral, technical, case)."""
    path = RUBRICS_DIR / f"{mode}.yaml"
    if not path.exists():
        path = RUBRICS_DIR / "behavioral.yaml"

    if yaml:
        with open(path) as f:
            return yaml.safe_load(f)

    return {
        "role": mode,
        "dimensions": [
            {"name": "overall", "weight": 1.0, "max_score": 5, "description": "Overall quality"},
        ],
    }
