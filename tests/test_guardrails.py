"""Unit tests for Guardrails."""

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from guardrails.filters import GuardrailsFilter


def test_disallowed_question():
    """Disallowed questions are blocked."""
    f = GuardrailsFilter()
    r = f.check_question("What is your age?")
    assert r.passed is False
    assert r.flagged is True


def test_allowed_question():
    """Normal questions pass."""
    f = GuardrailsFilter()
    r = f.check_question("Tell me about a time you showed leadership.")
    assert r.passed is True


def test_toxic_response():
    """Toxic content in response is blocked."""
    f = GuardrailsFilter()
    r = f.check_response("That idea is stupid and worthless.")
    assert r.passed is False
