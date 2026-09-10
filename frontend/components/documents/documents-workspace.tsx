"use client";

import { ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
import { CircleAlert, FileCheck2, FileText, Filter, LoaderCircle, Plus, RefreshCw, Search, Trash2, UploadCloud, X } from "lucide-react";
import { useAuth } from "@/components/providers/auth-provider";
import { useToast } from "@/components/providers/toast-provider";
import { ApiError, normalizeDocuments } from "@/lib/api";
import { formatBytes, formatDate } from "@/lib/format";
import type { DocumentRecord } from "@/lib/types";

export function DocumentsWorkspace() {
  const { apiFetch, user } = useAuth();
  const { showToast } = useToast();
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [knowledgeBase, setKnowledgeBase] = useState("");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [uploadKb, setUploadKb] = useState("default");
  const fileRef = useRef<HTMLInputElement>(null);
  const canWrite = user?.role !== "viewer";

  async function loadDocuments() {
    setLoading(true);
    try {
      const params = new URLSearchParams({ offset: "0", limit: "100" });
      if (knowledgeBase.trim()) params.set("knowledge_base_id", knowledgeBase.trim());
      const data = await apiFetch<unknown>(`/documents?${params.toString()}`);
      setDocuments(normalizeDocuments(data).documents);
    } catch (error) {
      showToast({ tone: "error", title: "Unable to load documents", description: error instanceof ApiError ? error.message : "Please try again." });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadDocuments(); }, [knowledgeBase]);

  const filtered = useMemo(() => documents.filter((document) => `${document.filename} ${document.knowledge_base_id} ${document.status}`.toLowerCase().includes(query.toLowerCase())), [documents, query]);
  const knowledgeBases = useMemo(() => [...new Set(documents.map((document) => document.knowledge_base_id))].sort(), [documents]);

  async function uploadDocument() {
    if (!file || !uploadKb.trim()) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("knowledge_base_id", uploadKb.trim());
      form.append("file", file);
      await apiFetch<unknown>("/documents", { method: "POST", body: form });
      showToast({ tone: "success", title: "Document indexed", description: `${file.name} is ready for RAG queries.` });
      setUploadOpen(false);
      setFile(null);
      await loadDocuments();
    } catch (error) {
      showToast({ tone: "error", title: "Upload failed", description: error instanceof ApiError ? error.message : "The document could not be uploaded." });
    } finally {
      setUploading(false);
    }
  }

  async function deleteDocument(document: DocumentRecord) {
    if (!confirm(`Delete ${document.filename}? This removes its vectors and database record.`)) return;
    setDeleting(document.id);
    try {
      await apiFetch<void>(`/documents/${encodeURIComponent(document.id)}`, { method: "DELETE" });
      setDocuments((items) => items.filter((item) => item.id !== document.id));
      showToast({ tone: "success", title: "Document deleted" });
    } catch (error) {
      showToast({ tone: "error", title: "Delete failed", description: error instanceof ApiError ? error.message : "The document could not be deleted." });
    } finally {
      setDeleting(null);
    }
  }

  function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] || null;
    if (selected && !selected.name.toLowerCase().endsWith(".pdf")) {
      showToast({ tone: "error", title: "PDF required", description: "Only PDF documents can be indexed by the current backend." });
      event.target.value = "";
      return;
    }
    setFile(selected);
  }

  return (
    <section className="page-workspace">
      <header className="page-header"><div><p className="eyebrow dark">Knowledge library</p><h1>Documents</h1><p>Upload, inspect, filter, and remove the PDFs available to your RAG workspace.</p></div>{canWrite ? <button className="primary-button" onClick={() => setUploadOpen(true)}><Plus size={17} /> Upload PDF</button> : null}</header>

      {!canWrite ? <div className="inline-banner compact"><CircleAlert size={18} /><div><strong>Viewer access</strong><p>You can inspect and query documents, but uploads and deletions are disabled.</p></div></div> : null}

      <div className="toolbar-card">
        <label className="search-field"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search filename, status, or knowledge base" /></label>
        <label className="filter-select"><Filter size={16} /><select value={knowledgeBase} onChange={(event) => setKnowledgeBase(event.target.value)}><option value="">All knowledge bases</option>{knowledgeBases.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
        <button className="icon-button bordered" onClick={() => void loadDocuments()} title="Refresh"><RefreshCw size={17} className={loading ? "spin" : ""} /></button>
      </div>

      <div className="document-summary"><span><strong>{filtered.length}</strong> documents shown</span><span><strong>{knowledgeBases.length}</strong> knowledge bases</span></div>

      {loading ? <div className="table-loader"><LoaderCircle size={25} className="spin" /><p>Loading documents…</p></div> : filtered.length ? (
        <div className="document-table-wrap"><table className="document-table"><thead><tr><th>Document</th><th>Knowledge base</th><th>Status</th><th>Size</th><th>Pages</th><th>Chunks</th><th>Added</th><th /></tr></thead><tbody>{filtered.map((document) => <tr key={document.id}><td><div className="document-name"><span className="file-icon"><FileText size={19} /></span><div><strong>{document.filename}</strong><small>{document.id}</small></div></div></td><td><span className="kb-pill">{document.knowledge_base_id}</span></td><td><span className={`status-badge status-${document.status.toLowerCase()}`}>{document.status === "completed" ? <FileCheck2 size={13} /> : null}{document.status}</span></td><td>{formatBytes(document.file_size_bytes)}</td><td>{document.total_pages ?? "—"}</td><td>{document.chunk_count ?? "—"}</td><td>{formatDate(document.created_at)}</td><td>{canWrite ? <button className="danger-icon-button" disabled={deleting === document.id} onClick={() => void deleteDocument(document)} title="Delete document">{deleting === document.id ? <LoaderCircle size={17} className="spin" /> : <Trash2 size={17} />}</button> : null}</td></tr>)}</tbody></table></div>
      ) : <div className="empty-state-card"><UploadCloud size={34} /><h2>No documents found</h2><p>Upload a PDF or adjust your filters.</p>{canWrite ? <button className="secondary-button" onClick={() => setUploadOpen(true)}>Upload your first PDF</button> : null}</div>}

      {uploadOpen ? <div className="modal-layer"><button className="modal-backdrop" onClick={() => !uploading && setUploadOpen(false)} aria-label="Close dialog" /><div className="modal-card" role="dialog" aria-modal="true" aria-labelledby="upload-title"><div className="modal-header"><div><h2 id="upload-title">Upload a PDF</h2><p>The backend will parse, chunk, embed, and index the document.</p></div><button className="icon-button" onClick={() => setUploadOpen(false)} disabled={uploading}><X size={19} /></button></div><div className="modal-body"><label className="field-label">Knowledge base ID<input className="text-input" value={uploadKb} onChange={(event) => setUploadKb(event.target.value)} placeholder="research-library" maxLength={128} /></label><button className={`drop-zone ${file ? "has-file" : ""}`} type="button" onClick={() => fileRef.current?.click()}><input ref={fileRef} type="file" accept="application/pdf,.pdf" hidden onChange={handleFile} />{file ? <><FileCheck2 size={30} /><strong>{file.name}</strong><span>{formatBytes(file.size)}</span></> : <><UploadCloud size={31} /><strong>Choose a PDF document</strong><span>Maximum size follows the backend upload limit</span></>}</button></div><div className="modal-footer"><button className="secondary-button" onClick={() => setUploadOpen(false)} disabled={uploading}>Cancel</button><button className="primary-button" onClick={() => void uploadDocument()} disabled={!file || !uploadKb.trim() || uploading}>{uploading ? <><LoaderCircle size={17} className="spin" /> Indexing…</> : <><UploadCloud size={17} /> Upload and index</>}</button></div></div></div> : null}
    </section>
  );
}
