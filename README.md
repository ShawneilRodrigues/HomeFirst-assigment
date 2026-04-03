# HomeFirst Voice Loan Counselor

Voice-first home loan counseling app built with Agno, FastAPI, Streamlit, Sarvam STT/TTS, and Chroma RAG.

## Features

- Voice and text chat for loan counseling
- Multilingual handling with language lock
- EMI and eligibility via deterministic tools
- Knowledge-grounded answers using Chroma vector store
- Session management in Streamlit with local + DB-backed persistence
- OpenRouter model support (currently `qwen/qwen3.6-plus:free`)

## Tech Stack

- Backend: FastAPI + Agno
- Frontend: Streamlit
- STT/TTS: Sarvam AI
- LLM: OpenRouter via Agno (`OpenRouter` model)
- Vector DB: Chroma (local `tmp/chromadb`)
- App persistence: PostgreSQL (local Docker setup by default)

## Project Structure

- `app/main.py`: FastAPI API (`/health`, `/api/text`, `/api/voice`)
- `app/counselor_agent.py`: Agent and model setup
- `app/tools.py`: EMI and eligibility tools
- `app/rag.py`: Knowledge + Chroma setup and ingestion logic
- `streamlit_app.py`: UI, voice flow, chat sessions
- `knowledge_base/docs/`: Knowledge files
- `knowledge_base/ingest.py`: Ingestion entrypoint
- `docker-compose.yml`: Local Postgres container
- `db/init.sql`: Session table bootstrap SQL

## Prerequisites

- Python 3.13+
- Docker Desktop (for local Postgres)
- Valid API keys:
  - `OPENROUTER_API_KEY`
  - `SARVAM_API_KEY`
  - `GOOGLE_API_KEY` (used for embeddings in current RAG config)

## Environment Setup

1. Create your env file:

```powershell
copy .env.example .env
```

2. Fill required values in `.env`:

- `OPENROUTER_API_KEY`
- `SARVAM_API_KEY`
- `GOOGLE_API_KEY`
- `DATABASE_URL` (default local Postgres works with compose)

Example local DB URL:

```env
DATABASE_URL=postgresql+psycopg://ai:ai@localhost:5432/homefirst
```

## Install Dependencies

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If you do not have `.venv` yet:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run the Complete System

### 1) Start local Postgres

```powershell
docker compose up -d postgres
docker compose ps
```

### 2) Verify DB connectivity

```powershell
.venv\Scripts\python.exe check_supabase_table.py
```

Expected output includes:

- `DB URL set: True`
- `Table: streamlit_sessions`

### 3) Ingest knowledge base into Chroma

```powershell
.venv\Scripts\python.exe knowledge_base/ingest.py
```

### 4) Start backend API

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 5) Start Streamlit UI (new terminal)

```powershell
.venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.port 8501
```

Open:

- API health: `http://127.0.0.1:8000/health`
- UI: `http://localhost:8501`

If 8501 is busy, use another port, for example:

```powershell
.venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.port 8506
```

## How to Use

- Use **Speak your message** for voice input, or chat input for text.
- The app keeps a chat session active for multi-turn conversation.
- Use the sidebar to create/switch chat sessions.
- Session persistence status appears in Debug Panel.

## API Endpoints

- `GET /health`
- `POST /api/text`
  - form-data: `message`, `session_id`, `user_id`
- `POST /api/voice`
  - form-data: `audio` (file), `session_id`, `user_id`

## Adding More Knowledge

1. Add files to `knowledge_base/docs/` (`.txt`, `.md`, `.markdown`)
2. Re-run ingestion:

```powershell
.venv\Scripts\python.exe knowledge_base/ingest.py
```

## Troubleshooting

### `httpx.ReadTimeout` in Streamlit

- Usually backend took too long to answer voice request.
- Retry once; if persistent, verify backend is healthy and OpenRouter key is valid.

### Backend fails on port 8000 (`WinError 10048`)

- Port already in use. Kill process on 8000 and restart backend.

### Streamlit port not available

- Start on a free port (e.g. `8502`, `8504`, `8506`).

### Docker/Postgres not reachable

- Ensure Docker Desktop is running.
- Check container status:

```powershell
docker compose ps
```

### RAG ingestion errors

- Ensure keys are set (`GOOGLE_API_KEY`) and docs exist in `knowledge_base/docs`.

## Security Notes

- Never commit `.env` to git.
- Rotate any API key immediately if exposed publicly.
