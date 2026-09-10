import type {
  DocumentRecord,
  OrganizationInfo,
  OrganizationMember,
  OrganizationRole,
  RagResponse,
  TokenBundle,
  UserProfile,
} from "@/lib/types";

export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  code: string;
  details: unknown;
  retryAfter?: number;
  requestId?: string;

  constructor(message: string, options: { status: number; code?: string; details?: unknown; retryAfter?: number; requestId?: string }) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code || "API_ERROR";
    this.details = options.details;
    this.retryAfter = options.retryAfter;
    this.requestId = options.requestId;
  }
}

export function requestId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `web-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

async function readBody(response: Response): Promise<unknown> {
  if (response.status === 204) return undefined;
  const text = await response.text();
  if (!text) return undefined;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

export async function parseResponse<T>(response: Response): Promise<T> {
  const body = await readBody(response);
  if (!response.ok) {
    const payload = typeof body === "object" && body !== null ? body as Record<string, unknown> : {};
    const error = typeof payload.error === "object" && payload.error !== null ? payload.error as Record<string, unknown> : payload;
    const retry = response.headers.get("retry-after");
    throw new ApiError(
      typeof error.message === "string" ? error.message : `Request failed with status ${response.status}.`,
      {
        status: response.status,
        code: typeof error.code === "string" ? error.code : undefined,
        details: error.details,
        retryAfter: retry ? Number(retry) : undefined,
        requestId: response.headers.get("x-request-id") || undefined,
      },
    );
  }
  return body as T;
}

export function buildHeaders(init?: HeadersInit): Headers {
  const headers = new Headers(init);
  headers.set("Accept", "application/json");
  headers.set("X-Request-ID", requestId());
  return headers;
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null ? value as Record<string, unknown> : {};
}

function stringValue(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function boolValue(value: unknown, fallback = true): boolean {
  return typeof value === "boolean" ? value : fallback;
}

function roleValue(value: unknown): OrganizationRole {
  return value === "owner" || value === "admin" || value === "member" || value === "viewer" ? value : "member";
}

export function normalizeUser(value: unknown): UserProfile {
  const root = asRecord(value);
  const data = asRecord(root.user ?? root.profile ?? root.data ?? value);
  return {
    id: stringValue(data.id ?? data.user_id),
    organization_id: stringValue(data.organization_id),
    email: stringValue(data.email),
    full_name: stringValue(data.full_name ?? data.name, stringValue(data.email, "User")),
    role: roleValue(data.role),
    is_active: boolValue(data.is_active),
  };
}

export function extractTokenBundle(value: unknown): TokenBundle {
  const root = asRecord(value);
  const candidate = root.tokens ?? root.data ?? value;
  const data = asRecord(candidate);
  const accessToken = stringValue(data.access_token ?? data.accessToken);
  const refreshToken = stringValue(data.refresh_token ?? data.refreshToken);
  if (!accessToken || !refreshToken) throw new ApiError("Authentication response did not contain both tokens.", { status: 500, code: "INVALID_AUTH_RESPONSE" });
  const userValue = data.user ?? data.profile ?? root.user ?? root.profile;
  return {
    accessToken,
    refreshToken,
    tokenType: stringValue(data.token_type ?? data.tokenType, "bearer"),
    expiresIn: typeof data.expires_in === "number" ? data.expires_in : undefined,
    user: userValue ? normalizeUser(userValue) : undefined,
  };
}

export function normalizeDocuments(value: unknown): { documents: DocumentRecord[]; total: number; offset: number; limit: number } {
  const outer = asRecord(value);
  const nested = outer.data;
  const root = asRecord(nested ?? value);
  const list = Array.isArray(value) ? value : Array.isArray(nested) ? nested : Array.isArray(root.documents) ? root.documents : Array.isArray(root.items) ? root.items : [];
  const documents = list.map((item) => {
    const data = asRecord(item);
    return {
      id: stringValue(data.id ?? data.document_id),
      knowledge_base_id: stringValue(data.knowledge_base_id),
      filename: stringValue(data.filename, "Untitled document"),
      status: stringValue(data.status, "unknown"),
      file_size_bytes: typeof data.file_size_bytes === "number" ? data.file_size_bytes : null,
      total_pages: typeof data.total_pages === "number" ? data.total_pages : null,
      chunk_count: typeof data.chunk_count === "number" ? data.chunk_count : null,
      embedding_provider: typeof data.embedding_provider === "string" ? data.embedding_provider : null,
      embedding_model: typeof data.embedding_model === "string" ? data.embedding_model : null,
      embedding_dimension: typeof data.embedding_dimension === "number" ? data.embedding_dimension : null,
      vector_store_provider: typeof data.vector_store_provider === "string" ? data.vector_store_provider : null,
      error_message: typeof data.error_message === "string" ? data.error_message : null,
      created_at: typeof data.created_at === "string" ? data.created_at : null,
      updated_at: typeof data.updated_at === "string" ? data.updated_at : null,
    } satisfies DocumentRecord;
  });
  return {
    documents,
    total: typeof root.total === "number" ? root.total : documents.length,
    offset: typeof root.offset === "number" ? root.offset : 0,
    limit: typeof root.limit === "number" ? root.limit : documents.length,
  };
}

export function normalizeRagResponse(value: unknown): RagResponse {
  const root = asRecord(value);
  const data = asRecord(root.data ?? value);
  const sourceList = Array.isArray(data.sources) ? data.sources : [];
  return {
    query: stringValue(data.query),
    answer: stringValue(data.answer),
    grounded: boolValue(data.grounded, false),
    citations: Array.isArray(data.citations) ? data.citations.filter((item): item is string => typeof item === "string") : [],
    sources: sourceList.map((source) => {
      const item = asRecord(source);
      return {
        citation_id: stringValue(item.citation_id),
        document_id: typeof item.document_id === "string" ? item.document_id : null,
        chunk_id: typeof item.chunk_id === "string" ? item.chunk_id : null,
        filename: typeof item.filename === "string" ? item.filename : null,
        page_number: typeof item.page_number === "number" ? item.page_number : null,
      };
    }),
    retrieved_chunk_count: typeof data.retrieved_chunk_count === "number" ? data.retrieved_chunk_count : sourceList.length,
  };
}

export function normalizeOrganization(value: unknown): OrganizationInfo {
  const outer = asRecord(value);
  const root = asRecord(outer.data ?? value);
  const data = asRecord(root.organization ?? root);
  return {
    id: stringValue(data.id ?? data.organization_id ?? root.organization_id),
    name: stringValue(data.name ?? root.organization_name, "Organization"),
    slug: typeof data.slug === "string" ? data.slug : undefined,
    membership_id: typeof root.membership_id === "string" ? root.membership_id : undefined,
    role: roleValue(root.role ?? data.role),
  };
}

export function normalizeMembers(value: unknown): OrganizationMember[] {
  const outer = asRecord(value);
  const nested = outer.data;
  const root = asRecord(nested ?? value);
  const list = Array.isArray(value) ? value : Array.isArray(nested) ? nested : Array.isArray(root.members) ? root.members : Array.isArray(root.items) ? root.items : [];
  return list.map((entry) => {
    const data = asRecord(entry);
    const user = asRecord(data.user);
    return {
      membership_id: stringValue(data.membership_id ?? data.id),
      user_id: stringValue(data.user_id ?? user.id),
      email: stringValue(data.email ?? user.email),
      full_name: stringValue(data.full_name ?? user.full_name ?? user.name, stringValue(data.email ?? user.email, "Member")),
      role: roleValue(data.role),
      is_active: boolValue(data.is_active),
      created_at: typeof data.created_at === "string" ? data.created_at : undefined,
    };
  });
}
