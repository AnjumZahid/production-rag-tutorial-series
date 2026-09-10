# Knowledge Chat Frontend

A complete Next.js frontend for the FastAPI RAG backend.

## Included

- Login and organization registration
- JWT access-token use and refresh-token rotation
- ChatGPT-style sidebar and responsive mobile drawer
- New chat, local recent chats, search, and deletion
- Document-grounded RAG requests with source cards
- Knowledge-base and document filtering
- PDF upload, listing, filtering, and deletion
- Organization member management
- Role-aware controls for owner/admin/member/viewer
- Health and readiness display
- Rate-limit and request-ID error handling
- Light and dark themes

## Important conversation limitation

The current backend does not have conversation or message tables. Therefore:

- Visible chat history is stored in browser `localStorage`.
- Each `/rag/query` request is answered independently by the backend.
- The frontend does not claim that earlier messages are included in LLM context.

When backend conversation endpoints are added, the `ChatProvider` can be replaced with server-backed persistence.

## Install inside your project

From:

```text
C:\Users\Admin\Downloads\rag_app
```

Copy the extracted folder as:

```text
C:\Users\Admin\Downloads\rag_app\frontend
```

Then run:

```powershell
cd C:\Users\Admin\Downloads\rag_app\frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

Keep the FastAPI backend running:

```powershell
cd C:\Users\Admin\Downloads\rag_app
uv run uvicorn backend.app.main:app --reload
```

## CORS requirement

Your backend CORS allowlist must include the frontend origins used in development, normally:

```text
http://localhost:3000
http://127.0.0.1:3000
```

Restart Uvicorn after changing the backend `.env`.

## Environment

`.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
NEXT_PUBLIC_APP_NAME=Knowledge Chat
```

## Validate

```powershell
npm run typecheck
npm run build
```

## API assumptions

The client follows the completed contract:

```text
POST /auth/register
POST /auth/login
POST /auth/refresh
POST /auth/logout
GET  /auth/me
GET  /documents
POST /documents
DELETE /documents/{document_id}
POST /rag/query
GET  /organizations/current
GET  /organizations/current/members
POST /organizations/current/members
PATCH /organizations/current/members/{membership_id}/role
DELETE /organizations/current/members/{membership_id}
GET /health/live
GET /health/ready
```

The normalizers in `lib/api.ts` accept common wrapper variations such as arrays versus `{items: []}` or `{documents: []}`.
