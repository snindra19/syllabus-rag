# SyllabusRAG

A RAG-powered chatbot that answers questions about ASU course syllabi. Upload a syllabus PDF, and the system parses, chunks, embeds, and indexes it — then answers natural-language questions grounded strictly in syllabus content with course-level citations.

## Architecture

```
PDF Upload → PyMuPDF text extraction → Claude Haiku (structured markdown) → Section chunking
    → OpenAI embeddings (text-embedding-3-small, 1536-dim) → PostgreSQL + pgvector

User Query → Hybrid search (vector cosine + full-text RRF fusion) → Cross-encoder reranking
    → Claude Haiku streaming response with citations
```

### Retrieval Pipeline

1. **Hybrid Search** — Combines pgvector cosine similarity (IVFFlat index) with PostgreSQL full-text search (GIN index on tsvector), merged via Reciprocal Rank Fusion (k=60)
2. **Cross-Encoder Reranking** — `ms-marco-MiniLM-L6-v2` rescores the top 15 candidates down to the top 5 for LLM context
3. **Per-Syllabus Retrieval** — When specific syllabi are selected, retrieves independently per syllabus with guaranteed inclusion of grading/exam sections via header-based lookup, avoiding cross-encoder bias against structured tables
4. **Grounded Generation** — Claude Haiku streams answers citing `[Course Code — Section]`, refusing to answer if context doesn't contain the information

### Ingestion Pipeline

1. **Text Extraction** — PyMuPDF extracts raw text from uploaded PDFs
2. **LLM Preprocessing** — Claude Haiku converts raw text into structured markdown following a standardized syllabus template (course info, schedule, grading, policies)
3. **Chunking** — Splits processed markdown at `##` and `###` header boundaries — no cross-section overlap to preserve semantic coherence
4. **Embedding & Storage** — OpenAI `text-embedding-3-small` embeds all chunks in a single batch call; stored in PostgreSQL with pgvector, tsvector (auto-populated via DB trigger), and trigram indexes

## Tech Stack

**Backend:** FastAPI, SQLAlchemy (async) + Alembic, PostgreSQL + pgvector, Anthropic Claude API, OpenAI Embeddings API, sentence-transformers (cross-encoder)  
**Frontend:** React 18, Tailwind CSS, Vite  
**Infrastructure:** Docker Compose (pgvector/pgvector:pg17)

## Project Structure

```
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Pydantic settings from .env
│   ├── chat/
│   │   ├── router.py            # POST /chat — streaming RAG responses
│   │   └── prompt_builder.py    # System prompt + context block assembly
│   ├── ingestion/
│   │   ├── router.py            # POST /upload, GET /syllabi, DELETE /syllabi/:id
│   │   ├── file_parser.py       # PyMuPDF text extraction
│   │   ├── llm_preprocessor.py  # Claude Haiku structured markdown conversion
│   │   └── chunker.py           # Markdown section chunking
│   ├── retrieval/
│   │   ├── hybrid_search.py     # Vector + FTS with RRF fusion
│   │   ├── reranker.py          # Cross-encoder reranking (async wrapper)
│   │   ├── vector_store.py      # pgvector insert + cosine search
│   │   └── embeddings.py        # OpenAI embedding generation
│   ├── db/
│   │   ├── database.py          # Async SQLAlchemy engine + session
│   │   ├── models.py            # Syllabus + Chunk ORM models
│   │   └── migrations/          # Alembic migrations (vector, tsvector, trigram indexes)
│   └── models/
│       └── schemas.py           # Pydantic request/response schemas
├── frontend/
│   └── src/
│       ├── App.jsx              # Main layout — sidebar + chat
│       ├── api/client.js        # API client with streaming support
│       └── components/
│           ├── ChatWindow.jsx   # Message thread with streaming tokens
│           ├── MessageBubble.jsx
│           ├── UploadPanel.jsx  # Drag-and-drop PDF upload
│           └── SyllabusList.jsx # Syllabus selection sidebar
├── docker-compose.yml           # PostgreSQL + pgvector container
├── SYLLABUS_TEMPLATE.md         # LLM preprocessing prompt template
└── .env.example                 # Environment variable template
```

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for PostgreSQL + pgvector)
- Anthropic API key
- OpenAI API key

### 1. Start the database

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy and fill in your API keys
cp ../.env.example .env

# Run migrations
alembic upgrade head

# Start the server
uvicorn main:app --reload --port 8001
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

The app runs at `http://localhost:5173` with the Vite dev server proxying API requests to the backend on port 8001.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload` | Upload a syllabus PDF/DOCX — runs full ingestion pipeline |
| `GET` | `/syllabi` | List all uploaded syllabi |
| `DELETE` | `/syllabi/{id}` | Delete a syllabus and its chunks (cascade) |
| `POST` | `/chat` | Stream a grounded answer (accepts `message` + optional `syllabus_ids`) |
| `GET` | `/health` | Liveness check |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `OPENAI_API_KEY` | OpenAI API key (embeddings) | — |
| `DATABASE_URL` | PostgreSQL connection string | — |
| `CHAT_MODEL` | Claude model for chat responses | `claude-haiku-4-5-20251001` |
| `PREPROCESSING_MODEL` | Claude model for syllabus parsing | `claude-haiku-4-5-20251001` |
| `EMBEDDING_MODEL` | OpenAI embedding model | `text-embedding-3-small` |
