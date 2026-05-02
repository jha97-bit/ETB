"""LangChain-based conversational orchestrator for mock interviews."""

from typing import Optional

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.schemas import (
    InterviewMode,
    AskQuestionRequest,
    AskQuestionResponse,
    QAPair,
)
from shared.config import get_settings
from .questions import QuestionBank
from evaluation.cases import find_case_for_question

# Hugging Face integration
try:
    from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
    HAS_HF = True
except ImportError:
    HAS_HF = False


SYSTEM_PROMPT = """You are an experienced mock interview coach conducting a {mode} interview.
Your role is to ask one clear, professional interview question at a time.

Rules:
- Ask exactly ONE question per turn.
- Do not give answers or hints unless the user explicitly asks for help.
- Adapt follow-up questions based on the candidate's previous answer to probe deeper.
- Keep questions relevant to the target role when provided: {target_role}
- Be supportive but professional.

Mode guidance:
- If mode is "case", treat it as a business analytics / product / data science case study: focus on framing the problem, defining success metrics, proposing data sources and analyses (funnels, cohorts, A/B tests), and recommending a clear product or business decision.
"""


def _format_messages_as_prompt(history: list, input_text: str, system: str) -> str:
    """Format chat messages as a single prompt for HF models (Mistral/Phi format)."""
    parts = [f"<s>[INST] {system} [/INST]\n"]
    for msg in history:
        if isinstance(msg, HumanMessage):
            parts.append(f"[INST] {msg.content} [/INST]\n")
        elif isinstance(msg, AIMessage):
            parts.append(f"{msg.content}\n")
    parts.append(f"[INST] {input_text} [/INST]\n")
    return "".join(parts)


class OrchestratorAgent:
    """Orchestrates interview flow: question selection, follow-ups, context awareness."""

    def __init__(self):
        settings = get_settings()
        self._llm = None
        if settings.hf_token and HAS_HF:
            try:
                model = HuggingFaceEndpoint(
                    repo_id=settings.hf_llm_model,
                    task="text-generation",
                    huggingfacehub_api_token=settings.hf_token,
                    max_new_tokens=256,
                    temperature=0.7,
                )
                self._llm = ChatHuggingFace(llm=model)
            except Exception:
                pass

        self._question_bank = QuestionBank()
        self._prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ])

    def ask_question(self, request: AskQuestionRequest) -> AskQuestionResponse:
        """Return the next interview question, optionally adapting to last answer."""
        mode = request.mode

        # First question: use question bank
        if not request.last_answer and not request.conversation_history:
            if mode == InterviewMode.CASE and (request.case_context or "").strip():
                question = self._generate_uploaded_case_question(request)
                hint = f"Scenario: {(request.case_context or '').strip()[:700]}"
                return AskQuestionResponse(
                    question=question,
                    mode=mode,
                    is_followup=False,
                    session_id=request.session_id,
                    hint=hint,
                )
            question, is_followup = self._question_bank.get_question(
                request.session_id, mode, is_followup=False
            )
            hint = self._build_case_hint(mode, question)
            return AskQuestionResponse(
                question=question,
                mode=mode,
                is_followup=False,
                session_id=request.session_id,
                hint=hint,
            )

        # Follow-up: use LLM to generate adaptive question
        if self._llm and request.last_answer and request.last_question:
            question = self._generate_followup(request)
            return AskQuestionResponse(
                question=question,
                mode=mode,
                is_followup=True,
                session_id=request.session_id,
                hint=None,
            )

        # Fallback: next from question bank
        question, _ = self._question_bank.get_question(
            request.session_id, mode, is_followup=True
        )
        return AskQuestionResponse(
            question=question,
            mode=mode,
            is_followup=True,
            session_id=request.session_id,
            hint=self._build_case_hint(mode, question),
        )

    def _build_case_hint(self, mode: InterviewMode, question: str) -> Optional[str]:
        """Attach scenario context for structured case-study prompts."""
        if mode != InterviewMode.CASE:
            return None
        case = find_case_for_question(question)
        if not case or not case.scenario:
            return None
        return f"Scenario: {case.scenario.strip()}"

    def _generate_followup(self, request: AskQuestionRequest) -> str:
        history = []
        if request.conversation_history:
            for qa in request.conversation_history[-6:]:
                history.append(HumanMessage(content=qa.question))
                history.append(AIMessage(content=f"[Candidate answered] {qa.answer}"))
        history.append(HumanMessage(content=request.last_question))
        history.append(AIMessage(content=f"[Candidate answered] {request.last_answer}"))

        system = SYSTEM_PROMPT.format(
            mode=request.mode.value,
            target_role=request.target_role or "General role",
        )
        input_text = (
            "Generate exactly ONE follow-up question to probe deeper based on the candidate's answer. "
            "Only output the question, nothing else."
        )
        if request.mode == InterviewMode.CASE and (request.case_context or "").strip():
            input_text += (
                f"\n\nCase context (user-uploaded): {(request.case_context or '').strip()[:1800]}\n"
                "Keep the follow-up tied to this specific case context."
            )

        try:
            messages = self._prompt.format_messages(
                mode=request.mode.value,
                target_role=request.target_role or "General role",
                history=history,
                input=input_text,
            )
            response = self._llm.invoke(messages)
            text = response.content.strip() if hasattr(response, "content") else str(response)
            return text.split("\n")[0].strip() or "Could you elaborate on that?"
        except Exception:
            question, _ = self._question_bank.get_question(
                request.session_id, request.mode, is_followup=True
            )
            return question

    def _generate_uploaded_case_question(self, request: AskQuestionRequest) -> str:
        """Generate first question from user-uploaded case context."""
        title = (request.case_title or "uploaded case").strip()
        context = (request.case_context or "").strip()
        if not self._llm:
            return (
                f"For the {title} case, what is your problem framing, what key metrics will you prioritize, "
                "and what initial hypotheses would you test first?"
            )
        try:
            system = SYSTEM_PROMPT.format(
                mode=request.mode.value,
                target_role=request.target_role or "General role",
            )
            prompt = (
                "You are given a user-uploaded business case context. Ask exactly ONE opening interview question "
                "that is specific to this case and encourages structured analysis. Output only the question.\n\n"
                f"Case title: {title}\n"
                f"Case context: {context[:2200]}"
            )
            messages = self._prompt.format_messages(
                mode=request.mode.value,
                target_role=request.target_role or "General role",
                history=[],
                input=prompt,
            )
            response = self._llm.invoke(messages)
            text = response.content.strip() if hasattr(response, "content") else str(response)
            return text.split("\n")[0].strip() or (
                f"For the {title} case, how would you structure your analysis and recommendation?"
            )
        except Exception:
            return (
                f"For the {title} case, how would you structure your analysis and recommendation?"
            )
