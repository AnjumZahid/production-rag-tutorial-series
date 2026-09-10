# Production-Grade Retrieval-Augmented Generation (RAG) Platform

A production-oriented Retrieval-Augmented Generation (RAG) application built step by step as part of my YouTube tutorial series.

This project goes beyond a basic “upload a PDF and ask questions” demo. The goal is to show how a more realistic AI application can be structured when we also need authentication, organizations, user roles, document management, vector search, rate limiting, security, testing, health checks, and a usable frontend.

The backend is built with **FastAPI and Python**, while the frontend uses **Next.js and TypeScript**. MySQL stores relational application data, Chroma handles vector search, Redis is used for rate limiting and protection, Hugging Face models generate embeddings, and Gemini is used as the Large Language Model (LLM).

---

## Application Preview

<img width="1916" height="922" alt="1" src="https://github.com/user-attachments/assets/58b8e4e5-5ea0-4f05-ab4f-3466366141cb" />


---

## What This Project Includes

- Retrieval-Augmented Generation (RAG)
- PDF document ingestion
- Text cleaning and chunking
- Hugging Face embeddings
- Chroma vector database
- Semantic retrieval
- Gemini LLM integration
- Grounded answers with source references
- FastAPI REST API
- Next.js frontend
- MySQL database
- Redis rate limiting
- JWT authentication
- Refresh-token flow
- Organizations and team members
- Role-Based Access Control (RBAC)
- Owner, Admin, Member, and Viewer roles
- Document upload and deletion
- Vector cleanup during document deletion
- Structured logging
- Structured API errors
- Security middleware
- Health and readiness checks
- Alembic database migrations
- Automated backend tests

---

## YouTube Tutorial Series

This repository is connected to my complete YouTube series where the application is developed step by step.

The **`main` branch contains the latest complete application**.

Each tutorial episode also has its own Git tag / GitHub Release so viewers can download the exact project state corresponding to that video.

### Links

# Connect

- 📚 [Complete RAG Tutorial Playlist](https://www.youtube.com/watch?v=lEc8LZ3xnlI&list=PLUnnqkRIf4Xw)
- 🎥 [YouTube Channel](https://www.youtube.com/@anjumzahid789)
- 💼 [LinkedIn](https://www.linkedin.com/in/anjumzahid789)
  
---


## High-Level Architecture

```text
User
 │
 ▼
Next.js Frontend
 │
 ▼
FastAPI Backend
 │
 ├── JWT Authentication
 ├── Role-Based Access Control
 ├── Document Management
 ├── RAG Query Service
 └── Rate Limiting
 │
 ├───────────────┬───────────────┬───────────────┐
 ▼               ▼               ▼               ▼
MySQL           Redis          Chroma        LLM Provider
                                  │               │
                                  ▼               ▼
                              Vector Search     Gemini
                                  │
                                  ▼
                           Relevant Chunks
                                  │
                                  └──────► Grounded Answer
```

---

## RAG Flow

```text
PDF Upload
   │
   ▼
PDF Loader
   │
   ▼
PDF Parser
   │
   ▼
Text Cleaner
   │
   ▼
Document Chunker
   │
   ▼
Embedding Model
   │
   ▼
Chroma Vector Database
```

When a user asks a question:

```text
User Question
    │
    ▼
Question Embedding
    │
    ▼
Similarity Search
    │
    ▼
Relevant Document Chunks
    │
    ▼
Prompt + Retrieved Context
    │
    ▼
Gemini LLM
    │
    ▼
Grounded Answer + Sources
```

---

# Project Structure

```text
rag_platform/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── app.py
│   │   │   ├── auth_routes.py
│   │   │   ├── auth_schemas.py
│   │   │   ├── dependencies.py
│   │   │   ├── document_management_routes.py
│   │   │   ├── document_schemas.py
│   │   │   ├── health_routes.py
│   │   │   ├── health_schemas.py
│   │   │   ├── middleware.py
│   │   │   ├── organization_routes.py
│   │   │   ├── organization_schemas.py
│   │   │   ├── rate_limit_middleware.py
│   │   │   ├── routes.py
│   │   │   └── schemas.py
│   │   │
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── jwt.py
│   │   │   ├── passwords.py
│   │   │   ├── roles.py
│   │   │   └── service.py
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── exceptions.py
│   │   │   └── logging.py
│   │   │
│   │   ├── database/
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py
│   │   │   │   ├── document.py
│   │   │   │   └── membership.py
│   │   │   │
│   │   │   ├── repositories/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth_repository.py
│   │   │   │   ├── document_repository.py
│   │   │   │   └── membership_repository.py
│   │   │   │
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── enums.py
│   │   │   └── session.py
│   │   │
│   │   ├── embeddings/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── factory.py
│   │   │   ├── huggingface.py
│   │   │   └── openai.py
│   │   │
│   │   ├── generation/
│   │   │   ├── __init__.py
│   │   │   ├── prompts.py
│   │   │   └── service.py
│   │   │
│   │   ├── ingestion/
│   │   │   ├── loaders/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   └── pdf_loader.py
│   │   │   │
│   │   │   ├── parsers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   └── pdf_parser.py
│   │   │   │
│   │   │   ├── processors/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── chunker.py
│   │   │   │   ├── metadata_builder.py
│   │   │   │   └── text_cleaner.py
│   │   │   │
│   │   │   └── __init__.py
│   │   │
│   │   ├── llms/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── factory.py
│   │   │   ├── gemini_ai.py
│   │   │   └── openai_provider.py
│   │   │
│   │   ├── organizations/
│   │   │   ├── __init__.py
│   │   │   └── service.py
│   │   │
│   │   ├── rate_limiting/
│   │   │   ├── __init__.py
│   │   │   ├── dependencies.py
│   │   │   ├── exceptions.py
│   │   │   └── service.py
│   │   │
│   │   ├── retrieval/
│   │   │   ├── __init__.py
│   │   │   └── service.py
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── document_ingestion.py
│   │   │   ├── document_management.py
│   │   │   ├── health_service.py
│   │   │   └── rag_query.py
│   │   │
│   │   ├── vectorstores/
│   │   │   ├── __init__.py
│   │   │   ├── chroma_store.py
│   │   │   ├── factory.py
│   │   │   └── qdrant_store.py
│   │   │
│   │   ├── __init__.py
│   │   └── main.py
│   │
│   └── __init__.py
│
├── data/
│   └── .gitkeep
│
├── docs/
│   ├── images/
│   │   ├── chat-rag.png
│   │   ├── dashboard.png
│   │   ├── documents.png
│   │   └── landing-page.png
│   │
│   └── who_pen_guidelines.pdf
│
├── frontend/
│   ├── app/
│   │   ├── (auth)/
│   │   │   └── ... authentication pages ...
│   │   ├── (dashboard)/
│   │   │   └── ... dashboard pages ...
│   │   ├── globals.css
│   │   ├── layout.tsx
│   │   └── page.tsx
│   │
│   ├── components/
│   │   ├── chat/
│   │   │   └── ... RAG/chat components ...
│   │   ├── documents/
│   │   │   └── ... document components ...
│   │   ├── layout/
│   │   │   └── ... shared layout components ...
│   │   ├── members/
│   │   │   └── ... member-management components ...
│   │   ├── providers/
│   │   │   └── ... React/global providers ...
│   │   └── settings/
│   │       └── ... settings components ...
│   │
│   ├── lib/
│   │   └── ... API/auth/helper logic ...
│   │
│   ├── .env.example
│   ├── .gitignore
│   ├── next-env.d.ts
│   ├── next.config.ts
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── pnpm-workspace.yaml
│   ├── README.md
│   ├── setup.ps1
│   ├── tsconfig.json
│   └── VALIDATION.md
│
├── frontend_contract/
│   ├── frontend.env.example
│   ├── openapi.json
│   └── README.md
│
├── migrations/
│   ├── versions/
│   │   ├── REVISION_create_document_registry_tables.py
│   │   └── REVISION_create_organization_membership_records.py
│   ├── env.py
│   ├── README
│   └── script.py.mako
│
├── scripts/
│   ├── __init__.py
│   ├── create_dev_token.py
│   └── export_openapi.py
│
├── tests/
│   ├── test_api_endpoints.py
│   ├── test_backend_contract.py
│   ├── test_chroma_store.py
│   ├── test_chunker.py
│   ├── test_database_connection.py
│   ├── test_document_ingestion_service.py
│   ├── test_document_management.py
│   ├── test_document_repository.py
│   ├── test_gemini_llm_provider.py
│   ├── test_generation_service.py
│   ├── test_health_endpoints.py
│   ├── test_huggingface_embeddings.py
│   ├── test_jwt_auth.py
│   ├── test_membership_foundation.py
│   ├── test_metadata_builder.py
│   ├── test_pdf_loader.py
│   ├── test_pdf_parser.py
│   ├── test_rate_limiting.py
│   ├── test_real_auth_flow.py
│   ├── test_real_component_interfaces.py
│   ├── test_real_document_ingestion.py
│   ├── test_real_rag_query.py
│   ├── test_retrieval_service.py
│   ├── test_role_authorization.py
│   ├── test_security_middleware.py
│   └── test_text_cleaner.py
│
├── .env.example
├── .env.docker.example
├── .gitignore
├── alembic.ini
├── compose.yml
├── pyproject.toml
└── uv.lock
```

---

# Running the Project

## 1. Clone the Repository

```bash
git clone https://github.com/AnjumZahid/production-rag-tutorial-series.git
cd production-rag-tutorial-series
```

## 2. Configure Backend Environment

Create your local `.env` file from the example:

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

Update the required database credentials, API keys, and other configuration values inside `.env`.

Never commit your real `.env` file.

## 3. Install Backend Dependencies

This project uses `uv` for Python dependency management.

```bash
uv sync
```

## 4. Start Required Services

MySQL and Redis can be started using Docker Compose:

```bash
docker compose up -d
```

## 5. Apply Database Migrations

```bash
uv run alembic upgrade head
```

## 6. Start the FastAPI Backend

```bash
uv run uvicorn backend.app.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

Swagger API documentation:

```text
http://127.0.0.1:8000/docs
```

## 7. Start the Frontend

Open another terminal:

```bash
cd frontend
```

Create the frontend environment file:

```powershell
Copy-Item .env.example .env.local
```

Install frontend dependencies:

```bash
pnpm install
```

Start Next.js:

```bash
pnpm dev
```

Open the frontend in your browser using the URL shown by Next.js.

---

# API Overview

The application includes APIs for:

```text
Authentication
├── Register
├── Login
├── Refresh Token
├── Logout
└── Current User

Organizations
├── Current Organization
├── List Members
├── Add Member
├── Update Member Role
└── Remove Member

Documents
├── Upload Document
├── List Documents
├── Get Document
└── Delete Document

RAG
└── Query uploaded knowledge

Health
├── Health
├── Liveness
└── Readiness
```

---

# Why This Repository Exists

There are already many good tutorials showing the basic Retrieval-Augmented Generation (RAG) workflow.

With this project, I wanted to focus on what happens after the basic RAG demo works.

How should users be authenticated?  
Where should application data be stored?  
How should team permissions work?  
What happens to vectors when a document is deleted?  
How should rate limiting, structured errors, testing, and health checks be handled?

These are the kinds of questions that start becoming important when a prototype grows into a real application.

The YouTube series follows the same idea. Instead of jumping directly to the final code, the project is built gradually so that each component and architectural decision can be understood separately.

---

# Contributing

This repository primarily supports the YouTube tutorial series, but suggestions, improvements, bug reports, and discussions are welcome.

If you find an issue while following one of the episodes, please open a GitHub Issue and mention the episode number you are following.

---

# Disclaimer

This project is intended for educational and development purposes.

Before using it in a real production environment, review the security configuration, secrets management, deployment architecture, monitoring, storage, backup strategy, LLM usage limits, and other requirements specific to your environment.

---

# Connect

- 📚 [Complete RAG Tutorial Playlist](https://www.youtube.com/watch?v=lEc8LZ3xnlI&list=PLUnnqkRIf4Xw)
- 🎥 [YouTube Channel](https://www.youtube.com/@anjumzahid789)
- 💼 [LinkedIn](https://www.linkedin.com/in/anjumzahid789)

If this project helps you understand Retrieval-Augmented Generation (RAG) or production-oriented AI application development, consider starring the repository and following the complete tutorial series.
