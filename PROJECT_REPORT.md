# Project Report: Mock Interview Platform (ETB)

**Document purpose:** Summary of goals, implementation, deployment, and outcomes for course or stakeholder review.

---

## 1. Executive summary

ETB is a **mock interview preparation system** that combines a **FastAPI** backend, a **Streamlit** web client, and **Hugging Face–hosted models** for adaptive questions and rubric-based feedback. Users practice **behavioral**, **technical**, and **case** interviews; the system supports **guardrails**, **session-scoped question banks**, **case study material** from curated files, optional **voice** endpoints (STT/TTS), and **cloud deployment** (e.g. Render) via environment-based configuration.

---

## 2. Project goals and objectives

| Goal | Description |
|------|-------------|
| **Realistic practice** | Deliver interview questions and follow-ups aligned to selected mode. |
| **Actionable feedback** | Score answers against YAML rubrics and return summaries, growth tips, and dimension scores. |
| **Case study depth** | Ground **case** mode in parsed scenarios from internal case packs and structured YAML. |
| **Safety** | Filter inappropriate user answers, generated questions, and feedback text where policies apply. |
| **Accessibility** | Allow teammates to use the app via a public URL without cloning the repo (deployed UI + API). |

---

## 3. System architecture

```
Streamlit (app.py)  ──HTTP──►  FastAPI (main.py)
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            OrchestratorAgent   EvaluationEngine   MemoryService
            + QuestionBank      + rubrics + cases   + Chroma
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
                            GuardrailsFilter
```

- **Orchestrator:** First question from **mode-specific banks**; follow-ups via **LLM** when configured; **case hints** from `find_case_for_question`.
- **Evaluation:** `POST /evaluate` loads rubrics (`behavioral`, `technical`, `case`, `testcases`) and returns structured results.
- **Memory:** Events and recall for personalization (vector store where enabled).
- **Guardrails:** Pre/post checks on answers, questions, and feedback; HITL events logged to `data/hitl_events.json`.
- **Voice (extension):** `POST /voice/start` and `POST /voice/ask` chain STT → same ask logic → TTS.

---

## 4. What was implemented

### 4.1 Backend (`main.py`, packages)

- REST API with **CORS** enabled for browser clients.
- Endpoints: `/ask_question`, `/evaluate`, `/memory/save`, `/memory/recall`, `/voice/start`, `/voice/ask`, `/tts`, root `/` for health checks.
- **Pydantic** request/response models in `shared/schemas.py` (`InterviewMode`, `AskQuestionRequest`, etc.).

### 4.2 Frontend (`app.py`)

- **Mock Interview Platform** UI: mode sidebar (caps labels + short descriptions), stacked **Question / Context / Answer** flow, answer template expander, feedback panels, session overview with **metrics**, **dataframe**, and **JSON download**.
- **`API_URL`** from environment for production; **health check with retries** for cold starts on free hosting.
- **Session reset** when interview type changes mid-session; **`web-{mode}`** session IDs so question banks do not cross-contaminate.
- Optional **embedded HTML** expander with `postMessage` bridge (`streamlit-javascript`).

### 4.3 Case content (`Case Studies/`, `evaluation/`)

- **`evaluation/cases.yaml`:** Curated case (e.g. new credit card partnership) with scenario, core question, good approaches, mistakes, follow-ups.
- **`evaluation/cases.py`:** Parses `.md` / `.txt` under `Case Studies/` (Practice Cases, Capital One BA magazine mini case, C1 notes, etc.) and merges with YAML; OCR-style cleanup and deduplication by title.
- **`orchestrator/questions.py`:** Banks for behavioral, technical, case (from `get_all_cases()`), and testcases strings.

### 4.4 Deployment

- **Dockerfile** runs API only (uvicorn); **Streamlit** documented as second process or second cloud service.
- **`.env.example`** documents `HUGGINGFACEHUB_API_TOKEN`, Chroma paths, optional **`API_URL`** for UI.

---

## 5. Technology stack

| Layer | Technologies |
|--------|----------------|
| API | FastAPI, Uvicorn |
| UI | Streamlit, pandas, streamlit-javascript (optional) |
| LLM / agents | LangChain, langchain-huggingface |
| Models / APIs | Hugging Face Hub (LLM, Whisper STT, TTS), sentence-transformers |
| Vectors | ChromaDB |
| Config | python-dotenv, Pydantic v2, PyYAML |
| Tests | pytest |

---

## 6. Testing and quality

- **`tests/`:** `test_orchestrator.py`, `test_memory.py`, `test_guardrails.py`.
- **Manual:** Swagger at `/docs`; Streamlit happy path for three modes; Render smoke tests for API + UI with `API_URL`.

---

## 7. Challenges and mitigations

| Challenge | Mitigation |
|-----------|------------|
| UI pointed at `localhost` when deployed | **`API_URL`** env var; document for Streamlit service. |
| Free-tier API **sleeps**; health check failed | **Longer timeouts**, **retries**, **Try again**; wake API in second tab. |
| Sidebar **mode** ≠ displayed **question** after switching type | **Clear session** on mode change; **per-mode `session_id`**. |
| Render defaulted to **Dockerfile** (API only) for Streamlit | Use **Python** runtime + **`streamlit run ...`** as start command for UI service. |
| **Duplicate case titles** when merging files | **Unique** first-line / title for supplemental MD; YAML + folder merge dedupes by title. |
| Heavy **Python dependencies** on free tier | Long builds; possible **RAM** limits—monitor logs; optional future slim requirements split. |

---

## 8. Limitations (current)

- **Voice UX** not fully integrated into main Streamlit flow (API exists; end-to-end voice UI is a natural next step).
- **`InterviewMode.TESTCASES`** in schema and bank but not necessarily exposed in Streamlit radio (three modes in main UI).
- **Ephemeral disk** on free PaaS may reset Chroma/local data on restart.
- **CORS `*`** acceptable for class demos; should be restricted for strict production.

---

## 9. Recommended future work

1. **Voice tab** in Streamlit: record/upload → `/voice/start` & `/voice/ask` → `st.audio`.
2. **Expose testcases mode** in UI if course requires QA-style interviews.
3. **`render.yaml`** or one-page deploy checklist in-repo for repeatability.
4. **Optional** requirements split: `requirements-api.txt` vs full stack for smaller images.

---

## 10. Conclusion

The project delivers a **working end-to-end mock interview stack**: configurable modes, case-backed prompts, LLM-assisted follow-ups, rubric evaluation, guardrails, and a **deployable** split of API + Streamlit. The architecture separates concerns cleanly (orchestrator, evaluation, memory, guardrails), and recent work focused on **reliability in real hosting** (env-based API URL, health checks, session/mode consistency) and **richer case corpora** under `Case Studies/`.

---

*Generated for the ETB / Mock Interview AI repository. Update section dates and deployment URLs when submitting to a specific course or sponsor.*
