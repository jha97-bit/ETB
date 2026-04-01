"""Case study definitions and helpers for evaluation and question selection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import List, Optional

import yaml


@dataclass
class CaseStudy:
    id: str
    title: str
    scenario: str
    core_question: str
    good_approach: List[str]
    common_mistakes: List[str]
    suggested_followups: List[str]


_CASES_PATH = Path(__file__).parent / "cases.yaml"
_PROJECT_CASES_DIR = Path(__file__).parent.parent / "Case Studies"
_CASES_CACHE: List[CaseStudy] | None = None


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u0085", " ")
    # Basic RTF cleanup for .txt files exported as rich text
    if text.lstrip().startswith("{\\rtf"):
        text = re.sub(r"\\[a-z]+\d* ?", " ", text)
        text = text.replace("{", " ").replace("}", " ")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _insert_missing_spaces(text: str) -> str:
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _collapse_repeated_title(text: str) -> str:
    t = text.strip()
    n = len(t)
    if n > 20 and n % 2 == 0:
        half = n // 2
        if t[:half].strip() == t[half:].strip():
            return t[:half].strip()
    return t


def _is_bad_title(title: str) -> bool:
    low = title.lower()
    bad_markers = [
        "provided data",
        "questions to answer",
        "math",
        "overview",
        "description",
        "introduction",
        "question 2",
        "question 3",
        "information sheet",
        "market size",
        "financial analysis",
        "potential framework",
        "potential issue tree",
    ]
    return any(marker in low for marker in bad_markers)


def _clean_title(raw_title: str) -> str:
    title = _insert_missing_spaces(raw_title.strip().rstrip(":"))
    title = _collapse_repeated_title(title)
    title = re.sub(
        r"(?i)\b(final questions and conclusions|provided data|questions to answer|math|information sheet|question \d+)\b.*$",
        "",
        title,
    ).strip()
    title = re.sub(r"\s{2,}", " ", title).strip()
    return title


def _reflow_ocr_linebreaks(body: str) -> str:
    """Turn hard line wraps from PDF/OCR into spaces so words aren't merged."""
    t = body.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"\n+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _strip_to_story_anchor(t: str) -> str:
    """Drop mangled PDF headers (e.g. 'P bl t t t ti 81 Problem...') before the real scenario."""
    for pat in (
        r"(?i)\bOur client\b",
        r"(?i)\bYour client\b",
        r"(?i)\bThe client is\b",
        r"(?i)\bYou are (?:the )?consultants\b",
    ):
        m = re.search(pat, t)
        if m:
            return t[m.start() :].strip()
    return t


def _fix_missing_sentence_punctuation(t: str) -> str:
    """Insert period before a new sentence when PDF lost punctuation."""
    starters = (
        "What|Which|Who|When|Where|Why|How|They|Our|If|The|Here|You|We|This|For|Drivers|"
        "Describe|Explain|List|Assume|Given|Your|A|An"
    )
    t = re.sub(rf"(?<=[a-z]) (?=(?:{starters})\b)", ". ", t)
    return t


def _strip_markdown_ocr_junk(t: str) -> str:
    """Remove page markers and stray ## headers from PDF exports."""
    t = re.sub(r"(?i)\s*##\s*\d+\s*", " ", t)
    t = re.sub(r"(?i)\s*##\s*introduction\s*", " ", t)
    t = re.sub(r"\s*##\s*\.?\s*", " ", t)
    # "can be 61 Introduction" style tail junk
    t = re.sub(r"(?i)\s*can be\s+\d+\s*introduction.*$", "", t)
    t = re.sub(r"(?i)\s+\d+\s+introduction\.?\s*$", "", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t


def _fix_split_and_merged_words(t: str) -> str:
    """Fix common OCR splits (cust omer) and accidental merges (clientisa)."""
    # Merged small words (no spaces in source)
    merged = {
        r"\bclientisa\b": "client is a",
        r"\bclientis\b": "client is",
        r"\bwhatdoyouthink\b": "what do you think",
    }
    for pat, repl in merged.items():
        t = re.sub(pat, repl, t, flags=re.IGNORECASE)
    # Split across line-wrap in OCR (word broken with space)
    splits = [
        (r"\bcust\s+omer\b", "customer"),
        (r"\bthi\s+nk\b", "think"),
        (r"\bprovi\s+der\b", "provider"),
        (r"\bservi\s+ce\b", "service"),
        (r"\btelecommuni\s+cations\b", "telecommunications"),
        (r"\bretenti\s+on\b", "retention"),
        (r"\bproble\s+ms\b", "problems"),
    ]
    for pat, repl in splits:
        t = re.sub(pat, repl, t, flags=re.IGNORECASE)
    # Heavy OCR: spaces inserted mid-word (consulting case pack)
    spaced = [
        (r"\bwhic h\b", "which"),
        (r"\bfr ozen\b", "frozen"),
        (r"\bdete rmine\b", "determine"),
        (r"\bdetermin e\b", "determine"),
        (r"\bnarra ti ve\b", "narrative"),
        (r"\boperat ing\b", "operating"),
        (r"\bmanufac turer\b", "manufacturer"),
        (r"\bmanufact urer\b", "manufacturer"),
        (r"\bpriv ate\b", "private"),
        (r"\bequi ty\b", "equity"),
        (r"\bfamil y\b", "family"),
        (r"\bown ed\b", "owned"),
        (r"\bbran ded\b", "branded"),
        (r"\beth nic\b", "ethnic"),
        (r"\bNort heast\b", "Northeast"),
        (r"\bNort h east\b", "Northeast"),
        # "Problem statement narrative" badly spaced
        (r"(?i)pro\s+bl\s+em\s+s\s+t\s+a\s+t\s+emen\s+t\s+narra\s+ti\s+ve", "Problem statement narrative"),
        (r"(?i)probl\s+em\s+s\s+t\s+a\s+t\s+emen\s+t", "problem statement"),
        (r"(?i)st\s+a\s+t\s+emen\s+t\s+narra\s+ti\s+ve", "statement narrative"),
        (r"\btr\s+ipling\b", "tripling"),
        (r"\bde\s+velop\b", "develop"),
        (r"\bclarif ying\b", "clarifying"),
    ]
    for pat, repl in spaced:
        t = re.sub(pat, repl, t)
    return t


def _dedupe_repeated_sentences(t: str) -> str:
    """Remove near-duplicate consecutive/overlapping sentences from OCR repeats."""
    parts = re.split(r"(?<=[.!?])\s+", t)
    seen: set[str] = set()
    out: List[str] = []
    for p in parts:
        p = p.strip()
        if len(p) < 15:
            continue
        key = re.sub(r"\s+", " ", p.lower())[:100]
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return " ".join(out)


def _clean_ocr_phrase(text: str) -> str:
    """Clean common OCR artifacts while staying conservative."""
    t = text
    t = re.sub(r"\s{2,}", " ", t)
    # Remove repeated phrase fragments (e.g., "Problem Statement Narrative Problem Statement Narrative")
    t = re.sub(
        r"(?i)\b(problem statement narrative|problem statement)\b(?:\s+\1\b)+",
        r"\1",
        t,
    )
    # Do NOT auto-merge generic "word1 sp sp2 sp3" patterns — it breaks phrases like "client is a".
    # Use explicit replacements only:
    explicit_splits = [
        (r"\bcomp\s+an\s+y\b", "company"),
        (r"\boptio\s+ns\b", "options"),
    ]
    for pat, repl in explicit_splits:
        t = re.sub(pat, repl, t, flags=re.IGNORECASE)
    # Common OCR split-word fixes seen in uploaded case pack.
    replacements = {
        r"\bcompan y\b": "company",
        r"\boptio ns\b": "options",
        r"\btarg eted\b": "targeted",
        r"\bexca vator\b": "excavator",
        r"\bproduc e\b": "produce",
        r"\bmark eting\b": "marketing",
        r"\bcust omer\b": "customer",
        r"\bprofitabilit y\b": "profitability",
    }
    for pattern, repl in replacements.items():
        t = re.sub(pattern, repl, t, flags=re.IGNORECASE)
    # Normalize extra spaces around punctuation
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t


def _extract_scenario(body: str) -> str:
    body = _reflow_ocr_linebreaks(body)
    body = _strip_to_story_anchor(body)
    lines = [ln.strip() for ln in body.splitlines()]
    if len(lines) <= 1:
        lines = [body]
    cleaned = []
    for ln in lines:
        if len(ln) < 25:
            continue
        if re.fullmatch(r"[\W_]+", ln):
            continue
        if ln.lower().startswith("case ") and ":" in ln:
            continue
        ln = re.sub(r"^#+\s*", "", ln).strip()
        ln = re.sub(r"\s*#+\s*", " ", ln).strip()
        ln = _clean_ocr_phrase(_insert_missing_spaces(ln))
        cleaned.append(ln)
        if len(cleaned) >= 8:
            break
    scenario_raw = _clean_ocr_phrase(" ".join(cleaned).strip())
    scenario_raw = _strip_to_story_anchor(scenario_raw)
    scenario_raw = _strip_markdown_ocr_junk(scenario_raw)
    scenario_raw = _fix_split_and_merged_words(scenario_raw)
    scenario_raw = _fix_missing_sentence_punctuation(scenario_raw)
    scenario_raw = _dedupe_repeated_sentences(scenario_raw)
    # Build scenario from first full sentences to avoid trailing incomplete fragments.
    sentence_candidates = re.split(r"(?<=[.!?])\s+", scenario_raw)
    picked: list[str] = []
    for s in sentence_candidates:
        s = s.strip()
        if len(s) < 25:
            continue
        if re.search(r"(?i)\b(question|provided data|math|overview)\b", s):
            continue
        picked.append(s)
        if len(picked) >= 3:
            break
    scenario = " ".join(picked) if picked else scenario_raw
    scenario = _clean_ocr_phrase(scenario)
    if len(scenario) > 700:
        scenario = scenario[:700].rstrip()
        end = max(scenario.rfind(". "), scenario.rfind("? "), scenario.rfind("! "))
        if end > 120:
            scenario = scenario[: end + 1]
    return scenario


def _default_good_approach() -> List[str]:
    return [
        "Clarify the objective, success metric, and constraints before jumping into analysis.",
        "Break the problem into a structured framework (funnel/cohorts/segments/hypotheses).",
        "Use relevant data and quantify impact with explicit assumptions.",
        "Recommend a decision with trade-offs, risks, and next validation steps.",
    ]


def _default_common_mistakes() -> List[str]:
    return [
        "Going straight to a solution without framing the problem or metrics.",
        "Using generic statements without data, assumptions, or prioritization.",
        "Ignoring stakeholder impact, feasibility, or experiment design.",
    ]


def _default_followups() -> List[str]:
    return [
        "Which metric would you prioritize first, and why?",
        "What assumptions in your analysis are most fragile?",
        "How would you test your recommendation before full rollout?",
    ]


def _make_case(case_id: str, title: str, scenario: str, core_question: str) -> CaseStudy:
    return CaseStudy(
        id=case_id,
        title=title.strip(),
        scenario=scenario.strip(),
        core_question=core_question.strip(),
        good_approach=_default_good_approach(),
        common_mistakes=_default_common_mistakes(),
        suggested_followups=_default_followups(),
    )


def _load_structured_yaml_cases() -> List[CaseStudy]:
    if not _CASES_PATH.exists():
        return []
    data = yaml.safe_load(_CASES_PATH.read_text()) or {}
    cases_raw = data.get("cases", [])
    return [
        CaseStudy(
            id=c["id"],
            title=c["title"],
            scenario=c.get("scenario", ""),
            core_question=c.get("core_question", ""),
            good_approach=c.get("good_approach", []) or _default_good_approach(),
            common_mistakes=c.get("common_mistakes", []) or _default_common_mistakes(),
            suggested_followups=c.get("suggested_followups", []) or _default_followups(),
        )
        for c in cases_raw
    ]


def _parse_case_file(path: Path) -> List[CaseStudy]:
    text = _normalize_text(path.read_text(errors="ignore"))
    # Build best title per case number from all occurrences in file.
    num_title_candidates: dict[str, List[str]] = {}
    for m in re.finditer(r"(?im)^(?:#+\s*)?case\s+(\d+)\s*[:\-]\s*(.+?)\s*$", text):
        num = m.group(1).strip()
        candidate = _clean_title(m.group(2))
        if candidate:
            num_title_candidates.setdefault(num, []).append(candidate)
    best_title_by_num: dict[str, str] = {}
    for num, cands in num_title_candidates.items():
        good = [c for c in cands if not _is_bad_title(c)]
        pool = good or cands
        best_title_by_num[num] = min(pool, key=len).strip()

    case_header = re.compile(r"(?im)^(?:#+\s*)?case\s+(\d+)\s*[:\-]\s*(.+?)\s*$")
    matches = list(case_header.finditer(text))
    parsed: List[CaseStudy] = []
    seen_case_numbers: set[str] = set()

    if matches:
        for idx, m in enumerate(matches):
            case_num = m.group(1).strip()
            if case_num in seen_case_numbers:
                continue
            start = m.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            body = text[start:end]
            title = best_title_by_num.get(case_num, _clean_title(m.group(2)))
            if _is_bad_title(title):
                continue
            scenario = _extract_scenario(body)
            if not scenario:
                continue
            case_id = f"{_slugify(path.stem)}_case_{case_num}_{_slugify(title)}"
            question = f"For the {title} case, how would you structure your analysis and recommendation?"
            parsed.append(_make_case(case_id, title, scenario, question))
            seen_case_numbers.add(case_num)
        return parsed

    # Fallback: treat the file as one case (useful for standalone text/RTF exports)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    title = path.stem
    for ln in lines[:40]:
        ln_clean = ln.strip().rstrip(":")
        if len(ln_clean) < 8:
            continue
        if any(x in ln_clean.lower() for x in ["fonttbl", "colortbl", "cocoartf", "tx560"]):
            continue
        if "\\" in ln_clean:
            continue
        if re.search(r"credit card|case|partner|market|customer|product", ln_clean.lower()):
            title = ln_clean
            break
    title = _clean_title(title)
    scenario = _extract_scenario("\n".join(lines[1:]))
    if not scenario:
        scenario = " ".join(lines[1:6])[:900]
    case_id = f"{_slugify(path.stem)}_single"
    question = f"For the {title} case, how would you structure your analysis and recommendation?"
    return [_make_case(case_id, title, scenario, question)]


def _load_professor_cases() -> List[CaseStudy]:
    if not _PROJECT_CASES_DIR.exists():
        return []
    files = sorted(
        [p for p in _PROJECT_CASES_DIR.iterdir() if p.is_file() and p.suffix.lower() in {".md", ".txt"}]
    )
    parsed: List[CaseStudy] = []
    for p in files:
        parsed.extend(_parse_case_file(p))
    return parsed


def _load_cases() -> List[CaseStudy]:
    global _CASES_CACHE
    if _CASES_CACHE is not None:
        return _CASES_CACHE

    # Prefer professor-provided folder cases; keep YAML as explicit curated additions.
    combined = _load_professor_cases() + _load_structured_yaml_cases()
    deduped: dict[str, CaseStudy] = {}
    for case in combined:
        key = case.title.strip().lower()
        if key and key not in deduped:
            deduped[key] = case
    _CASES_CACHE = list(deduped.values())
    return _CASES_CACHE


def get_all_cases() -> List[CaseStudy]:
    return _load_cases()


def find_case_for_question(question: str) -> Optional[CaseStudy]:
    """Best-effort mapping from question text to a known case study."""
    question_lower = (question or "").lower()
    for case in _load_cases():
        if case.title.lower() in question_lower:
            return case
        if "credit card" in question_lower and "credit card" in case.scenario.lower():
            return case
    return None

