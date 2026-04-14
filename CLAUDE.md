# Syllabus Chatbot - Project Rules

## Overview
RAG-based chatbot that answers questions about ASU course syllabi. Users upload syllabus files (PDF or DOCX), the system parses and indexes them, and a chat interface lets users ask questions grounded in the syllabus content.

## Tech Stack
- **Backend:** FastAPI (Python 3.11+)
- **File Parsing:** pymupdf for PDFs, pandoc for DOCX — extracts raw text
- **LLM Preprocessing:** Claude Haiku 4.5 API to convert raw text into structured markdown (using SYLLABUS_TEMPLATE.md prompt)
- **Embeddings:** OpenAI text-embedding-3-small
- **Vector Store:** PostgreSQL + pgvector (hybrid search: vector similarity + full-text search)
- **LLM for Chat:** Claude Haiku 4.5 API (claude-haiku-4-5-20241022) via anthropic SDK. Can swap to Sonnet for better accuracy later — just a config change.
- **Reranking:** cross-encoder/ms-marco-MiniLM-L6-v2 via sentence-transformers
- **Frontend:** React with Tailwind CSS
- **Environment:** Windows, development in PowerShell

## Project Structure
```
syllabus-chatbot/
├── CLAUDE.md
├── SYLLABUS_TEMPLATE.md          # LLM prompt template for parsing
├── backend/
│   ├── main.py                   # FastAPI app entry point
│   ├── config.py                 # Settings, API keys, DB config
│   ├── requirements.txt
│   ├── ingestion/
│   │   ├── file_parser.py        # pymupdf (PDF) + pandoc (DOCX) raw text extraction
│   │   ├── llm_preprocessor.py   # Claude Haiku API structured markdown conversion
│   │   └── chunker.py            # Markdown header-based chunking (## and ###)
│   ├── retrieval/
│   │   ├── embeddings.py         # OpenAI embedding generation
│   │   ├── vector_store.py       # pgvector operations
│   │   ├── hybrid_search.py      # Combined vector + BM25/full-text search
│   │   └── reranker.py           # Cross-encoder reranking
│   ├── chat/
│   │   ├── router.py             # /chat endpoint
│   │   └── prompt_builder.py     # System prompt + context assembly
│   ├── models/
│   │   └── schemas.py            # Pydantic models
│   └── db/
│       ├── database.py           # SQLAlchemy/asyncpg setup
│       └── migrations/           # Alembic migrations
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx
│   │   │   ├── MessageBubble.jsx
│   │   │   ├── UploadPanel.jsx
│   │   │   └── SyllabusList.jsx
│   │   └── api/
│   │       └── client.js         # API calls to backend
│   └── tailwind.config.js
└── data/
    ├── raw_uploads/              # Original uploaded files (PDF/DOCX)
    └── processed_markdown/       # LLM-cleaned markdown files
```

## Architecture Flow
1. File Upload → detect type (PDF/DOCX) → extract raw text (pymupdf or pandoc)
2. Raw text → Claude Haiku API with SYLLABUS_TEMPLATE.md prompt → structured markdown
3. Store raw text + processed markdown in PostgreSQL (syllabi table)
4. Markdown → chunk by ## and ### headers with ~50 token overlap
5. Chunks → OpenAI embeddings → store in pgvector with metadata (course name, section header)
6. User query → embed query → hybrid search (vector + full-text) → retrieve top 15 chunks
7. Top 15 → cross-encoder reranker → select top 5
8. Top 5 chunks + user query + system prompt → Claude Haiku API → grounded answer with citations

## Parsed Syllabus Sections (from SYLLABUS_TEMPLATE.md)
- Course Information (code, title, semester, credits, schedule line number)
- Instructor & Staff (name, email, office, phone, zoom, TA/IA/RA details)
- Office Hours (instructor + TA, location, zoom)
- Communication Policy (preferred method, response time, platform rules)
- Course Description
- Enrollment Requirements / Prerequisites
- Course Objectives
- Expected Learning Outcomes
- Grading Policies (breakdown table, grade scale, extra credit, late submission, grade appeals)
- Attendance / Absence Policy
- Course Tools & Platforms (Canvas, Slack, languages, frameworks)
- Textbooks / Materials (optional — not always present)
- AI Usage / Generative AI Policy
- Academic Integrity (course-specific rules only)
- ASU-Wide Policies (brief summary — disability, Title IX, copyright, etc.)
- Additional Course Information

## Code Style
- Use async/await throughout FastAPI
- Type hints on all functions
- Pydantic models for all request/response schemas
- Environment variables for all API keys and secrets (use python-dotenv)
- Never hardcode API keys
- Keep functions small and single-purpose
- Add docstrings to all public functions

## Key Rules
- NEVER hallucinate answers. If retrieved context doesn't contain the answer, say "I don't have that information in the uploaded syllabi."
- Always cite which course syllabus and section the answer comes from
- Store both raw text and processed markdown for verification
- Flag any document where processed markdown is significantly shorter than raw text (possible data loss)
- Log all LLM API calls with token counts for cost tracking
- Use streaming responses for the chat endpoint
- Handle file parsing failures gracefully with clear error messages
- ASU boilerplate policies: parse once, tag as shared — don't duplicate per syllabus

## Database Schema (pgvector)
- syllabi table: id, filename, course_code, course_title, upload_date, raw_text, processed_markdown, metadata (JSONB)
- chunks table: id, syllabus_id, section_header, content, embedding (vector(1536)), is_asu_boilerplate (boolean)
- Enable pg_trgm and tsvector for full-text search on chunks

## Environment Variables Needed
- ANTHROPIC_API_KEY
- OPENAI_API_KEY
- DATABASE_URL (PostgreSQL connection string)

## Model Swapping
Models are config values in .env. To upgrade accuracy, just change:
- CHAT_MODEL=claude-haiku-4-5-20241022 → claude-sonnet-4-6-20250514
- PREPROCESSING_MODEL=claude-haiku-4-5-20241022 → claude-sonnet-4-6-20250514
