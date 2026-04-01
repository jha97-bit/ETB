"""Question bank for Behavioral, Technical, Case, and Test Cases interview modes."""

from shared.schemas import InterviewMode
from evaluation.cases import get_all_cases

BEHAVIORAL_QUESTIONS = [
    "Tell me about a time when you had to deal with a difficult teammate. How did you handle it?",
    "Describe a situation where you had to meet a tight deadline. What was your approach?",
    "Give an example of when you showed leadership without formal authority.",
    "Tell me about a time you failed. What did you learn from it?",
    "Describe a project where you had to learn something new quickly.",
    "Tell me about a time when you had to persuade someone to see things your way.",
    "Give an example of working effectively under pressure.",
    "Describe a situation where you received critical feedback. How did you respond?",
    "Tell me about a time you had to work with someone you didn't get along with.",
    "Describe an occasion when you had to make an unpopular decision.",
]

TECHNICAL_QUESTIONS = [
    "Explain how you would design a URL shortening service like bit.ly.",
    "Describe the difference between REST and GraphQL. When would you use each?",
    "How would you debug a memory leak in a production application?",
    "Explain the CAP theorem and its implications for distributed systems.",
    "Describe your approach to writing maintainable, testable code.",
    "How would you optimize a slow database query?",
    "Explain the difference between SQL and NoSQL databases. Give use cases for each.",
    "Describe how you would implement rate limiting in an API.",
    "How do you approach code reviews? What do you look for?",
    "Explain how version control (e.g., Git) has helped you in a project.",
]

_CASES = get_all_cases()

_GENERIC_CASE_FALLBACK = [
    "Your product’s weekly active users have dropped by 15% after a recent UI redesign. As a business analyst/product manager, how would you frame the problem, what hypotheses would you generate, and what data would you pull to validate them?",
    "Sign-up conversion on your landing page has fallen from 25% to 15% in the last month. Walk through how you would analyze the funnel, segment users, and design experiments (A/B tests or otherwise) to identify the root cause.",
    "You shipped a new recommendation model that improves click-through rate but decreases time-on-site and user retention. How would you evaluate this trade-off, what additional metrics would you look at, and what decision would you recommend?",
]

CASE_QUESTIONS = [c.core_question for c in _CASES] or _GENERIC_CASE_FALLBACK

TESTCASES_QUESTIONS = [
    "You're given a login screen (email + password + 'Remember me'). Walk me through the test cases you'd write, including edge cases and negative scenarios.",
    "How would you design test cases for a search feature with filters, sorting, and pagination? What would you prioritize first?",
    "Given an API endpoint `POST /orders` that creates an order, what functional and non-functional test cases would you cover (validation, error handling, idempotency, concurrency)?",
    "Explain equivalence partitioning and boundary value analysis, then apply them to an input field that accepts ages 18–65.",
    "How would you test a checkout/payment flow end-to-end? Include failure modes (timeouts, declined cards), retries, and data integrity checks.",
    "A bug report says: 'App crashes when uploading an image.' How would you reproduce it, isolate the cause, and add regression tests?",
    "How do you decide what to automate vs keep manual? Describe your criteria and how you'd structure an automation suite.",
    "Design test cases for a CSV import feature. Consider file size limits, encoding, malformed rows, duplicates, and rollback behavior.",
    "How would you test offline mode in a mobile app with background sync and conflict resolution? What are the highest-risk scenarios?",
    "If you only had 30 minutes to test a new release, how would you perform risk-based testing and choose your 'must-run' test cases?",
]

MODE_QUESTIONS = {
    InterviewMode.BEHAVIORAL: BEHAVIORAL_QUESTIONS,
    InterviewMode.TECHNICAL: TECHNICAL_QUESTIONS,
    InterviewMode.CASE: CASE_QUESTIONS,
    InterviewMode.TESTCASES: TESTCASES_QUESTIONS,
}


class QuestionBank:
    """Selects and tracks questions for interview sessions."""

    def __init__(self):
        self._asked: dict[str, set[int]] = {}  # session_id -> set of question indices

    def get_question(
        self, session_id: str, mode: InterviewMode, is_followup: bool = False
    ) -> tuple[str, bool]:
        """Get next question for session. Returns (question, is_followup)."""
        pool = MODE_QUESTIONS.get(mode, BEHAVIORAL_QUESTIONS)
        if session_id not in self._asked:
            self._asked[session_id] = set()

        asked = self._asked[session_id]
        available = [i for i in range(len(pool)) if i not in asked]
        if not available:
            # Reset for this session
            self._asked[session_id] = set()
            available = list(range(len(pool)))

        import random
        idx = random.choice(available)
        self._asked[session_id].add(idx)
        return pool[idx], is_followup
