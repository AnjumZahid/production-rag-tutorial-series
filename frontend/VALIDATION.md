# Frontend Validation

Validated on June 26, 2026.

## Checks passed

```text
npm install
npm run typecheck
npm run build
npm audit --omit=dev
npm run start
```

Results:

```text
TypeScript: passed
Next.js production build: passed
Dependency audit: 0 vulnerabilities
Production server startup: passed
```

Runtime route checks:

```text
/          -> 307 redirect to authentication/chat flow
/login     -> 200
/register  -> 200
/chat      -> 200
/documents -> 200
/members   -> 200
/settings  -> 200
```

## Backend integration requirement

The backend must be running at the URL configured in `.env.local` and its CORS allowlist must include the frontend development origin.

## Conversation limitation

Visible chat history is stored in browser local storage. The existing backend RAG endpoint processes each question independently and does not yet persist conversation messages or include earlier turns as LLM context.
