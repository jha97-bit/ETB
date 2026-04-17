"""Evaluation engine: rubric scoring and LLM critiques."""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage

import sys
import logging
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.schemas import (
    InterviewMode,
    EvaluateResponseRequest,
    EvaluateResponseResult,
    DimensionScore,
)
from shared.config import get_settings
from .rubrics import load_rubric
from .cases import find_case_for_question

logger = logging.getLogger(__name__)

# Hugging Face integration
try:
    from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
    HAS_HF = True
except ImportError:
    HAS_HF = False


EVAL_PROMPT = """You are an expert interview evaluator. Score the candidate's response using the rubric and (if provided) case study details below.

Question: {question}
Answer: {answer}
Interview Mode: {mode}
Target Role (if relevant): {target_role}

Rubric dimensions:
{rubric_text}

Case study context (may be empty):
{case_context}

For each dimension, provide:
1. A score from 0 to max_score (inclusive)
2. Brief constructive feedback (1-2 sentences)
3. For behavioral mode: assess STAR compliance (Situation, Task, Action, Result) - true/false
4. For case mode: treat it as a business analytics / product / data science case study and focus feedback on problem framing, data/metric choices, analytical rigor, and business impact

Respond in this exact JSON format (no other text):
{{
  "dimensions": [
    {{"name": "dimension_name", "score": <float>, "max_score": 5, "feedback": "<brief feedback>"}},
    ...
  ],
  "summary_feedback": "<2-3 sentence overall feedback>",
  "growth_tips": ["<actionable tip 1>", "<tip 2>", ...],
  "star_compliance": true/false
}}
"""


class EvaluationEngine:
    """Evaluates responses using rubrics and LLM critiques."""

    def __init__(self):
        settings = get_settings()
        self._llm = None
        logger.info(
            "Initializing EvaluationEngine: has_hf_token=%s HAS_HF_lib=%s",
            bool(settings.hf_token),
            HAS_HF,
        )
        if settings.hf_token and HAS_HF:
            try:
                model = HuggingFaceEndpoint(
                    repo_id=settings.hf_llm_model,
                    task="text-generation",
                    huggingfacehub_api_token=settings.hf_token,
                    max_new_tokens=512,
                    temperature=0.3,
                )
                self._llm = ChatHuggingFace(llm=model)
                logger.info("EvaluationEngine HF model initialized successfully")
            except Exception as e:
                logger.exception("Failed to initialize HF evaluation model: %s", e)

        self._prompt = ChatPromptTemplate.from_template(EVAL_PROMPT)

    def evaluate_response(self, request: EvaluateResponseRequest) -> EvaluateResponseResult:
        """Score and provide feedback for a candidate response."""
        rubric = load_rubric(request.mode.value)
        rubric_text = "\n".join(
            f"- {d['name']} (max {d['max_score']}): {d['description']}"
            for d in rubric.get("dimensions", [])
        )

        case = find_case_for_question(request.question)
        if case:
            bullets = "\n".join(f"- {b}" for b in case.good_approach)
            mistakes = "\n".join(f"- {m}" for m in case.common_mistakes)
            case_context = (
                f"Case title: {case.title}\n"
                f"Scenario: {case.scenario}\n"
                f"Ideal elements of a strong answer:\n{bullets}\n"
                f"Common mistakes to watch for:\n{mistakes}\n"
            )
        else:
            case_context = "None provided."

        if self._llm:
            result = self._eval_with_llm(request, rubric_text, case_context)
            if result:
                return result

        return self._eval_fallback(request, rubric)

    def _eval_with_llm(
        self, request: EvaluateResponseRequest, rubric_text: str, case_context: str
    ) -> Optional[EvaluateResponseResult]:
        try:
            msg = self._prompt.format(
                question=request.question,
                answer=request.answer,
                mode=request.mode.value,
                target_role=request.target_role or "N/A",
                rubric_text=rubric_text,
                case_context=case_context,
            )
            response = self._llm.invoke([HumanMessage(content=msg)], max_tokens=512)
            text = response.content if hasattr(response, "content") else str(response)

            import json
            import re
            json_match = re.search(r"\{[\s\S]*\}", text)
            if json_match:
                data = json.loads(json_match.group())
                dims = [
                    DimensionScore(
                        dimension=d["name"],
                        score=float(d.get("score", 0)),
                        max_score=float(d.get("max_score", 5)),
                        feedback=d.get("feedback", ""),
                    )
                    for d in data.get("dimensions", [])
                ]
                overall = sum(d.score for d in dims) / len(dims) if dims else 0

                # Coerce star_compliance to a proper boolean or None
                raw_star = data.get("star_compliance", None)
                star_bool: Optional[bool]
                if isinstance(raw_star, bool) or raw_star is None:
                    star_bool = raw_star
                elif isinstance(raw_star, str):
                    lowered = raw_star.strip().lower()
                    if lowered in ("true", "yes", "y", "1"):
                        star_bool = True
                    elif lowered in ("false", "no", "n", "0"):
                        star_bool = False
                    else:
                        star_bool = None
                else:
                    star_bool = None

                result = EvaluateResponseResult(
                    overall_score=round(overall, 1),
                    max_score=5.0,
                    dimensions=dims,
                    summary_feedback=data.get("summary_feedback", ""),
                    growth_tips=data.get("growth_tips", []),
                    star_compliance=star_bool,
                )
                logger.info("EvaluationEngine LLM evaluation succeeded")
                return result
        except Exception as e:
            logger.exception("EvaluationEngine LLM call failed: %s", e)
        return None

    def _eval_fallback(
        self, request: EvaluateResponseRequest, rubric: dict
    ) -> EvaluateResponseResult:
        """Fallback when LLM is unavailable."""
        dims_data = rubric.get("dimensions", [{"name": "overall", "max_score": 5}])
        dims = [
            DimensionScore(
                dimension=d["name"],
                score=3.0,
                max_score=float(d.get("max_score", 5)),
                feedback="Using a simple baseline evaluation because AI-powered feedback is temporarily unavailable (e.g., network or model error).",
            )
            for d in dims_data
        ]
        return EvaluateResponseResult(
            overall_score=3.0,
            max_score=5.0,
            dimensions=dims,
            summary_feedback="AI-powered evaluation was unavailable for this request, so a basic baseline score was returned instead. Check your internet connection and, if issues persist, verify your Hugging Face configuration.",
            growth_tips=[
                "Re-run the evaluation to see if AI feedback becomes available.",
                "If problems continue, verify your Hugging Face token and network connectivity.",
            ],
        )
