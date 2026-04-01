"""Guardrail policy configuration."""

from pathlib import Path

try:
    import yaml
    with open(Path(__file__).parent / "policy.yaml") as f:
        GUARDRAIL_POLICY = yaml.safe_load(f)
except Exception:
    GUARDRAIL_POLICY = {
        "safety": [
            {"type": "toxicity", "action": "block"},
            {"type": "bias", "action": "flag"},
        ],
        "disallowed_questions": [
            "What is your age?",
            "Are you married?",
            "Do you have children?",
            "What is your religion?",
        ],
        "feedback_rules": [
            "Feedback must be constructive and supportive",
            "Never use harsh or demeaning language",
        ],
    }
