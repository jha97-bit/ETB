# ETB — Documentation

Quick reference for the **Mock Interview Platform** (ETB). For a fuller project report, see **`PROJECT_REPORT.md`**.

---

## 1. What this is

- **Backend:** FastAPI app (`main.py`) — questions, evaluation, memory, guardrails, voice helpers.  
- **Frontend:** Streamlit app (`app.py`) — interview UI, feedback, session export.  
- **AI:** Hugging Face (LLM, optional STT/TTS) + local Chroma for memory when configured.

---

## 2. Prerequisites

- Python **3.9+** (3.11 recommended).  
- A **[Hugging Face token](https://huggingface.co/settings/tokens)** with read access.  
- Git (optional, for version control).

---

## 3. Local setup

```bash
cd "/path/to/ETB Project"
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit **`.env`**: set `HUGGINGFACEHUB_API_TOKEN=hf_...` (and other vars if needed). **Do not commit `.env`.**

---

## 4. Running the app

**Terminal 1 — API**

```bash
source venv/bin/activate
python main.py
```

Default: **http://localhost:8000** — Open **http://localhost:8000/docs** for Swagger.

**Terminal 2 — UI**

```bash
source venv/bin/activate
streamlit run app.py
```

Default: **http://localhost:8501**

**Optional:** `./run_prototype.sh` starts API in background then Streamlit (see script for behavior).

---

## 5. Environment variables

| Variable | Purpose |
|----------|---------|
| `HUGGINGFACEHUB_API_TOKEN` | Required for LLM, embeddings, HF STT/TTS. |
| `API_URL` | Used by Streamlit when API is not on localhost (e.g. `https://your-api.onrender.com`). |
| `CHROMA_PERSIST_DIR` | Where Chroma stores data (default in `.env.example`). |
| `HF_*` model overrides | Optional; see `.env.example`. |

---

## 6. Repository layout (high level)

| Path | Role |
|------|------|
| `main.py` | FastAPI entrypoint |
| `app.py` | Streamlit UI |
| `orchestrator/` | Questions + LangChain agent |
| `evaluation/` | Rubrics, case YAML, case parsing |
| `memory/` | Memory service + Chroma |
| `guardrails/` | Filters, policy, optional dashboard |
| `voice_agent/` | STT/TTS + voice orchestration |
| `shared/` | Schemas, config |
| `Case Studies/` | `.md` / `.txt` case source files |
| `tests/` | pytest |
| `scripts/` | Example curl scripts |

---

## 7. Main API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/ask_question` | Next interview question |
| POST | `/evaluate` | Score and feedback for an answer |
| POST | `/memory/save` | Save a memory event |
| POST | `/memory/recall` | Recall context |
| POST | `/voice/start` | First question + audio (form data) |
| POST | `/voice/ask` | User audio → next question + audio |
| GET | `/` | Health / service identity |

---

## 8. Deployment (short)

- Deploy **API** and **Streamlit** as **two** services (e.g. Render).  
- Set **`HUGGINGFACEHUB_API_TOKEN`** on the API service.  
- Set **`API_URL`** on the Streamlit service to the **public API base URL** (no trailing slash).  
- Free tiers may **sleep** — first request after idle can take **30–60+ seconds**; use “Try again” / refresh on the UI if needed.

---

## 9. Tests

```bash
source venv/bin/activate
pytest tests/ -v
```

---

## 10. Related files

- **`PROJECT_REPORT.md`** — Goals, architecture, challenges, limitations, future work.  
- **`README.md`** — Original course-style README and architecture diagram.  
- **`.env.example`** — Full list of env vars.

---

*Last updated: project documentation bundle. Adjust paths if your clone lives in a different directory.*
