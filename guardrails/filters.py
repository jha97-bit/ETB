"""Safety filters: toxicity, bias, disallowed content."""

from dataclasses import dataclass
import re
from typing import Optional

from .policy import GUARDRAIL_POLICY


@dataclass
class FilterResult:
    """Result of applying guardrail filters."""

    passed: bool
    flagged: bool
    reason: Optional[str] = None
    action: str = "allow"  # allow, flag, block


class GuardrailsFilter:
    """Applies guardrail policy to questions and responses."""

    def __init__(self):
        self._policy = GUARDRAIL_POLICY
        self._disallowed = set(
            q.lower().strip()
            for q in self._policy.get("disallowed_questions", [])
        )

    def check_question(self, question: str) -> FilterResult:
        """Check if a question violates policy (e.g., inappropriate)."""
        q_lower = question.lower().strip()
        for disallowed in self._disallowed:
            if not disallowed:
                continue
            if disallowed in q_lower or (len(q_lower) <= len(disallowed) and q_lower in disallowed):
                return FilterResult(
                    passed=False,
                    flagged=True,
                    reason=f"Question may be discriminatory or inappropriate: {disallowed}",
                    action="block",
                )
        return FilterResult(passed=True, flagged=False)

    def check_response(self, text: str) -> FilterResult:
        """Check user response for safety (toxicity, etc.)."""
        if not text or not text.strip():
            return FilterResult(passed=True, flagged=False)

        # Simple heuristic checks (can be replaced with Rebuff/Guardrails AI)
        toxic_words = ["hate", "kill", "stupid", "idiot", "worthless"]
        text_lower = text.lower()
        for w in toxic_words:
            # Whole words only — avoid false positives (e.g. "skill" matching "kill").
            if re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", text_lower):
                return FilterResult(
                    passed=False,
                    flagged=True,
                    reason="Response contains potentially harmful content.",
                    action="block",
                )
        return FilterResult(passed=True, flagged=False)

    def check_feedback(self, feedback: str) -> FilterResult:
        """Ensure feedback is constructive per policy."""
        harsh = ["terrible", "awful", "pathetic", "useless", "failure"]
        fb_lower = feedback.lower()
        for w in harsh:
            if w in fb_lower:
                return FilterResult(
                    passed=False,
                    flagged=True,
                    reason="Feedback violates constructive feedback policy.",
                    action="flag",
                )
        return FilterResult(passed=True, flagged=False)
