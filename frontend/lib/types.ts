export type OrganizationRole = "owner" | "admin" | "member" | "viewer";

export interface UserProfile {
  id: string;
  organization_id: string;
  email: string;
  full_name: string;
  role: OrganizationRole;
  is_active: boolean;
}

export interface TokenBundle {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn?: number;
  user?: UserProfile;
}

export interface DocumentRecord {
  id: string;
  knowledge_base_id: string;
  filename: string;
  status: string;
  file_size_bytes?: number | null;
  total_pages?: number | null;
  chunk_count?: number | null;
  embedding_provider?: string | null;
  embedding_model?: string | null;
  embedding_dimension?: number | null;
  vector_store_provider?: string | null;
  error_message?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface RagSource {
  citation_id: string;
  document_id?: string | null;
  chunk_id?: string | null;
  filename?: string | null;
  page_number?: number | null;
}

export interface RagResponse {
  query: string;
  answer: string;
  grounded: boolean;
  citations: string[];
  sources: RagSource[];
  retrieved_chunk_count: number;
}

export type ChatMessageRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
  createdAt: string;
  grounded?: boolean;
  sources?: RagSource[];
  requestId?: string;
  failed?: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  knowledgeBaseId: string;
  documentId: string | null;
  topK: number;
  messages: ChatMessage[];
}

export interface OrganizationInfo {
  id: string;
  name: string;
  slug?: string;
  membership_id?: string;
  role: OrganizationRole;
}

export interface OrganizationMember {
  membership_id: string;
  user_id: string;
  email: string;
  full_name: string;
  role: OrganizationRole;
  is_active: boolean;
  created_at?: string;
}
