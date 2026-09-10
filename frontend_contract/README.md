# Frontend API Handoff

## Base URL

Development:

```text
http://127.0.0.1:8000/api/v1
```

Frontend environment variable:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

## Authentication

Protected requests use:

```http
Authorization: Bearer <access_token>
```

Do not include `Bearer` when pasting the token into the Swagger authorization box. Swagger adds it automatically.

Access tokens expire after the configured short lifetime. Refresh tokens are used to obtain new access tokens.

## Authentication Endpoints

```text
POST /auth/register
POST /auth/login
POST /auth/refresh
POST /auth/logout
GET  /auth/me
```

## Organization Endpoints

```text
GET    /organizations/current
GET    /organizations/current/members
POST   /organizations/current/members
PATCH  /organizations/current/members/{membership_id}/role
DELETE /organizations/current/members/{membership_id}
```

## Document Endpoints

```text
POST   /documents
GET    /documents
GET    /documents/{document_id}
DELETE /documents/{document_id}
```

Document upload uses:

```text
multipart/form-data
```

Required fields:

```text
knowledge_base_id
file
```

## RAG Endpoint

```text
POST /rag/query
```

Example request:

```json
{
  "knowledge_base_id": "test-kb",
  "query": "What does the document recommend?",
  "k": 3,
  "document_id": "optional-document-id"
}
```

## Health Endpoints

```text
GET /health
GET /health/live
GET /health/ready
```

Use `/health/live` to confirm that the API process is alive.

Use `/health/ready` to confirm that MySQL and Redis are available.

## Roles

```text
owner
admin
member
viewer
```

| Operation | Owner | Admin | Member | Viewer |
|---|---:|---:|---:|---:|
| Query RAG | Yes | Yes | Yes | Yes |
| List documents | Yes | Yes | Yes | Yes |
| View document | Yes | Yes | Yes | Yes |
| Upload document | Yes | Yes | Yes | No |
| Delete document | Yes | Yes | Yes | No |
| Manage members | Yes | Yes | No | No |

## Standard Error Shape

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message.",
    "details": null
  }
}
```

Common status codes:

```text
400 Invalid request
401 Authentication failure
403 Authorization failure
404 Resource not found
409 Duplicate or conflicting resource
422 Validation error
429 Rate limit exceeded
500 Internal application failure
503 Required dependency unavailable
```

## Rate Limiting

Rate-limited responses return:

```text
Retry-After
X-RateLimit-Limit
X-RateLimit-Remaining
X-RateLimit-Reset
```

General API responses may include:

```text
X-RateLimit-Global-Limit
X-RateLimit-Global-Remaining
X-RateLimit-Global-Reset
```

When receiving `429`, the frontend should temporarily disable the action and show the retry duration.

## Request Tracing

Responses include:

```text
X-Request-ID
X-Process-Time-Ms
```

The frontend should record `X-Request-ID` when reporting an API failure.

A valid client-generated request ID may be sent through:

```http
X-Request-ID: frontend-request-12345
```

## Security Response Headers

Responses include:

```text
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
Permissions-Policy
```

## Token Handling

Recommended browser approach:

```text
Keep the access token in application memory
Use the refresh workflow when access expires
Clear authentication state on logout
Do not print tokens to the browser console
Do not include tokens in URLs
```

The exact refresh-token storage strategy will be finalized when the frontend authentication flow is implemented.

## OpenAPI Contract

The machine-readable API contract is:

```text
frontend_contract/openapi.json
```

It can be used to generate TypeScript types and API clients.