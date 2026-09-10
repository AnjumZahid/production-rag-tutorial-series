"use client";

import Link from "next/link";
import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import { ArrowUp, BookOpen, Check, ChevronDown, Copy, FileText, Info, LoaderCircle, PanelTop, RotateCcw, Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useAuth } from "@/components/providers/auth-provider";
import { useChats } from "@/components/providers/chat-provider";
import { useToast } from "@/components/providers/toast-provider";
import { ApiError, normalizeDocuments, normalizeRagResponse } from "@/lib/api";
import type { ChatMessage, DocumentRecord, RagSource } from "@/lib/types";

const suggestions = [
  "Summarize the main recommendations in my documents.",
  "What evidence supports the document's conclusion?",
  "List the most important limitations mentioned in the sources.",
  "Compare the key concepts across the uploaded documents.",
];

export function ChatWorkspace() {
  const { apiFetch } = useAuth();
  const { activeConversation, appendMessage, updateConversationSettings } = useChats();
  const { showToast } = useToast();
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [sending, setSending] = useState(false);
  const [input, setInput] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const response = await apiFetch<unknown>("/documents?offset=0&limit=100");
        if (active) setDocuments(normalizeDocuments(response).documents);
      } catch (error) {
        if (error instanceof ApiError) showToast({ tone: "error", title: "Documents could not be loaded", description: error.message });
      } finally {
        if (active) setLoadingDocs(false);
      }
    }
    void load();
    return () => { active = false; };
  }, [apiFetch, showToast]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [activeConversation?.messages.length, sending]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "0px";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 190)}px`;
  }, [input]);

  const knowledgeBases = useMemo(() => [...new Set(documents.map((document) => document.knowledge_base_id).filter(Boolean))].sort(), [documents]);
  const relevantDocuments = useMemo(() => documents.filter((document) => !activeConversation?.knowledgeBaseId || document.knowledge_base_id === activeConversation.knowledgeBaseId), [activeConversation?.knowledgeBaseId, documents]);

  useEffect(() => {
    if (!activeConversation || activeConversation.knowledgeBaseId || !knowledgeBases.length) return;
    updateConversationSettings(activeConversation.id, { knowledgeBaseId: knowledgeBases[0] });
  }, [activeConversation, knowledgeBases, updateConversationSettings]);

  if (!activeConversation) return <div className="workspace-loader"><span className="spinner" /></div>;

  async function sendMessage(text: string) {
    const clean = text.trim();
    if (!clean || sending || !activeConversation) return;
    if (!activeConversation.knowledgeBaseId.trim()) {
      showToast({ tone: "error", title: "Select a knowledge base", description: "Upload a document or enter the knowledge base ID before asking a question." });
      return;
    }

    const conversationId = activeConversation.id;
    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: "user", content: clean, createdAt: new Date().toISOString() };
    appendMessage(conversationId, userMessage);
    setInput("");
    setSending(true);

    try {
      const payload = {
        knowledge_base_id: activeConversation.knowledgeBaseId.trim(),
        query: clean,
        k: activeConversation.topK,
        document_id: activeConversation.documentId || undefined,
      };
      const response = await apiFetch<unknown>("/rag/query", { method: "POST", body: JSON.stringify(payload) });
      const result = normalizeRagResponse(response);
      appendMessage(conversationId, {
        id: crypto.randomUUID(),
        role: "assistant",
        content: result.answer || "I could not generate an answer from the available sources.",
        createdAt: new Date().toISOString(),
        grounded: result.grounded,
        sources: result.sources,
      });
    } catch (error) {
      const apiError = error instanceof ApiError ? error : null;
      let message = apiError?.message || "The answer could not be generated.";
      if (apiError?.status === 429 && apiError.retryAfter) message = `${message} Try again in about ${apiError.retryAfter} seconds.`;
      appendMessage(conversationId, {
        id: crypto.randomUUID(),
        role: "assistant",
        content: message,
        createdAt: new Date().toISOString(),
        requestId: apiError?.requestId,
        failed: true,
      });
    } finally {
      setSending(false);
      window.setTimeout(() => textareaRef.current?.focus(), 50);
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    void sendMessage(input);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendMessage(input);
    }
  }

  async function copyText(id: string, content: string) {
    await navigator.clipboard.writeText(content);
    setCopied(id);
    window.setTimeout(() => setCopied(null), 1400);
  }

  return (
    <section className="chat-workspace">
      <header className="chat-header">
        <div>
          <div className="chat-title-row"><h1>{activeConversation.title}</h1><span className="mode-pill"><BookOpen size={13} /> Document Q&amp;A</span></div>
          <p>Answers use the selected knowledge base and cite retrieved document evidence.</p>
        </div>
        <button className="ghost-button" onClick={() => setSettingsOpen((value) => !value)}><PanelTop size={17} /> Retrieval settings <ChevronDown size={15} className={settingsOpen ? "rotate-180" : ""} /></button>
      </header>

      {settingsOpen ? (
        <div className="retrieval-settings">
          <label><span>Knowledge base</span><input list="knowledge-bases" value={activeConversation.knowledgeBaseId} onChange={(event) => updateConversationSettings(activeConversation.id, { knowledgeBaseId: event.target.value, documentId: null })} placeholder="e.g. research-library" /><datalist id="knowledge-bases">{knowledgeBases.map((item) => <option key={item} value={item} />)}</datalist></label>
          <label><span>Document filter</span><select value={activeConversation.documentId || ""} onChange={(event) => updateConversationSettings(activeConversation.id, { documentId: event.target.value || null })}><option value="">All documents</option>{relevantDocuments.map((document) => <option key={document.id} value={document.id}>{document.filename}</option>)}</select></label>
          <label><span>Retrieved chunks</span><select value={activeConversation.topK} onChange={(event) => updateConversationSettings(activeConversation.id, { topK: Number(event.target.value) })}><option value={3}>3 focused</option><option value={5}>5 balanced</option><option value={8}>8 broad</option><option value={12}>12 extensive</option></select></label>
        </div>
      ) : null}

      <div className="chat-scroll-area">
        {!loadingDocs && documents.length === 0 ? (
          <div className="inline-banner"><Info size={18} /><div><strong>No documents are indexed yet.</strong><p>Upload a PDF before asking document-grounded questions.</p></div><Link href="/documents">Open documents</Link></div>
        ) : null}

        {activeConversation.messages.length === 0 ? (
          <div className="empty-chat">
            <div className="empty-chat-logo"><Sparkles size={30} /></div>
            <h2>What would you like to know?</h2>
            <p>Ask a question about your uploaded PDFs. Every response is generated from retrieved evidence rather than general chat memory.</p>
            <div className="suggestion-grid">{suggestions.map((suggestion) => <button key={suggestion} onClick={() => void sendMessage(suggestion)}><span>{suggestion}</span><ArrowUp size={16} /></button>)}</div>
          </div>
        ) : (
          <div className="message-thread">
            {activeConversation.messages.map((message) => (
              <article className={`message ${message.role} ${message.failed ? "failed" : ""}`} key={message.id}>
                <div className="message-avatar">{message.role === "assistant" ? <Sparkles size={17} /> : "You"}</div>
                <div className="message-body">
                  <div className="message-meta"><strong>{message.role === "assistant" ? "Knowledge Chat" : "You"}</strong>{message.role === "assistant" && message.grounded ? <span className="grounded-label"><Check size={12} /> Grounded</span> : null}</div>
                  <div className="markdown"><ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown></div>
                  {message.requestId ? <p className="request-id">Request ID: {message.requestId}</p> : null}
                  {message.sources?.length ? <SourceList sources={message.sources} /> : null}
                  {message.role === "assistant" && !message.failed ? <div className="message-actions"><button onClick={() => void copyText(message.id, message.content)}>{copied === message.id ? <Check size={15} /> : <Copy size={15} />} {copied === message.id ? "Copied" : "Copy"}</button></div> : null}
                </div>
              </article>
            ))}
            {sending ? <article className="message assistant"><div className="message-avatar"><Sparkles size={17} /></div><div className="message-body"><div className="message-meta"><strong>Knowledge Chat</strong></div><div className="thinking"><span /><span /><span /> Retrieving evidence and drafting an answer…</div></div></article> : null}
            <div ref={endRef} />
          </div>
        )}
      </div>

      <div className="composer-zone">
        <form className="composer" onSubmit={handleSubmit}>
          <textarea ref={textareaRef} value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={handleKeyDown} rows={1} maxLength={4000} placeholder="Ask a question about your documents…" aria-label="Message" />
          <div className="composer-bottom"><div className="composer-context"><FileText size={14} /><span>{activeConversation.documentId ? "1 selected document" : activeConversation.knowledgeBaseId ? activeConversation.knowledgeBaseId : "Choose a knowledge base"}</span></div><button className="send-button" type="submit" disabled={sending || !input.trim()} aria-label="Send message">{sending ? <LoaderCircle size={18} className="spin" /> : <ArrowUp size={18} />}</button></div>
        </form>
        <p className="composer-note">This version stores the visible conversation locally; each backend RAG request is answered independently.</p>
      </div>
    </section>
  );
}

function SourceList({ sources }: Readonly<{ sources: RagSource[] }>) {
  const [open, setOpen] = useState(false);
  return (
    <div className="sources-block">
      <button className="sources-toggle" onClick={() => setOpen((value) => !value)}><BookOpen size={15} /> {sources.length} source{sources.length === 1 ? "" : "s"}<ChevronDown size={14} className={open ? "rotate-180" : ""} /></button>
      {open ? <div className="source-grid">{sources.map((source, index) => <div className="source-card" key={`${source.citation_id}-${index}`}><span>{source.citation_id || `S${index + 1}`}</span><div><strong>{source.filename || "Document source"}</strong><p>{source.page_number ? `Page ${source.page_number}` : "Page not specified"}</p></div></div>)}</div> : null}
    </div>
  );
}
