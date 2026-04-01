# Mock Interview Preparation AI Agent

An intelligent AI agent for conducting mock interviews with students preparing for internships and job opportunities. The system features adaptive questioning, contextual memory, personalized feedback, and an optional **voice-based interface** for realistic spoken interview practice.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VOICE AGENT (Extension)                              │
│  Speech-to-Text → Orchestrator → Text-to-Speech │  Natural spoken interview  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────┼───────────────────────────────────────┐
│  A. CONVERSATIONAL ORCHESTRATOR     │  Dynamic question selection, follow-ups │
│     /ask_question                   │  Behavioral / Technical / Case modes   │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      │
┌─────────────────────────────────────┼───────────────────────────────────────┐
│  B. MEMORY & PERSONALIZATION        │  save_event(), recall_context()        │
│     Short-term │ Episodic │ Long-term│  Vector store, weak-skill tracking     │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      │
┌─────────────────────────────────────┼───────────────────────────────────────┐
│  C. EVALUATION & FEEDBACK           │  evaluate_response(), rubric scoring   │
│     STAR technique, LLM critiques   │  Growth tips, self-critique option     │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      │
┌─────────────────────────────────────┼───────────────────────────────────────┐
│  D. GUARDRAILS & HITL DASHBOARD     │  Toxicity/bias filters, mentor UI      │
│     Take-over button, event flags   │  Psychological safety                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Getting Started

### 1. Set Up the Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template and add your API keys
cp .env.example .env
```

### 2. Project Structure (Suggested)

```
etb-project/
├── orchestrator/          # Student A: LangChain agent, /ask_question API
├── memory/                # Student B: Memory manager, vector store
├── evaluation/            # Student C: Rubrics, evaluate_response(), feedback
├── guardrails/            # Student D: Rebuff/Guardrails, HITL dashboard
├── voice_agent/           # Extension: STT, TTS, voice orchestration
├── shared/                # Common schemas, types, config
└── tests/
```

### 3. Development Order (Dependencies)

| Phase | Component | Depends On |
|-------|-----------|------------|
| 1 | **Memory (B)** | None – start here; others need your `save_event` / `recall_context` stub |
| 2 | **Orchestrator (A)** | Memory stub from B |
| 3 | **Evaluation (C)** | Orchestrator Q&A output; writes to Memory |
| 4 | **Guardrails (D)** | A, B, C APIs for wrapping |
| 5 | **Voice Agent** | Orchestrator + Memory; optionally Evaluation for feedback |

---

## Voice Agent Extension

The voice agent layer enables **spoken mock interviews**:

1. **Speech-to-Text (STT)**: Hugging Face Inference API (Whisper)  
2. **Orchestrator integration**: User speech → `/ask_question` → next prompt  
3. **Text-to-Speech (TTS)**: Hugging Face Inference API (e.g., facebook/mms-tts-eng)  
4. **Context**: Same memory (B) and evaluation (C) as text mode

---

## Student Roles Summary

| Student | Focus | Key Deliverables |
|---------|-------|------------------|
| **A** | Conversational Orchestrator | Question engine, `/ask_question` API, cURL client, unit tests |
| **B** | Memory & Personalization | Memory service, `save_event`/`recall_context`, schema docs |
| **C** | Evaluation & Feedback | `evaluate_response` API, rubric JSON/YAML, demo notebook |
| **D** | Guardrails & HITL | Guardrail policy, Streamlit/Next.js dashboard, Dockerfile |

---

## Run the Project

```bash
# Install & activate
pip install -r requirements.txt
cp .env.example .env
# Add HUGGINGFACEHUB_API_TOKEN to .env

# Start API
python main.py
# or: uvicorn main:app --reload

# Run tests
pytest tests/ -v

# HITL Dashboard (separate terminal)
streamlit run guardrails/dashboard.py

# Sample API calls
bash scripts/curl_examples.sh
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ask_question` | POST | Get next interview question |
| `/memory/save` | POST | Save event to memory |
| `/memory/recall` | POST | Recall context |
| `/evaluate` | POST | Evaluate response, get scorecard + feedback |
| `/voice/ask` | POST | Voice: process speech, return question + audio |
| `/voice/start` | POST | Voice: get first question as text + audio |
| `/tts` | POST | Synthesize text to speech |

API docs: `http://localhost:8000/docs`

---

## API Keys You’ll Need

- **Hugging Face** (required): [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) → create token with read access
- Add to `.env`: `HUGGINGFACEHUB_API_TOKEN=hf_...`
- Powers: LLM (Mistral), embeddings (sentence-transformers), Whisper (STT), TTS

See `.env.example` for all variables.
