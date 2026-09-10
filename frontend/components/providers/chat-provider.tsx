"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "@/components/providers/auth-provider";
import { shortTitle } from "@/lib/format";
import type { ChatMessage, Conversation } from "@/lib/types";

interface ChatContextValue {
  conversations: Conversation[];
  activeConversation: Conversation | null;
  activeId: string | null;
  createConversation: () => string;
  selectConversation: (id: string) => void;
  deleteConversation: (id: string) => void;
  appendMessage: (conversationId: string, message: ChatMessage) => void;
  updateConversationSettings: (conversationId: string, settings: Partial<Pick<Conversation, "knowledgeBaseId" | "documentId" | "topK">>) => void;
  clearAll: () => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

function newConversation(): Conversation {
  const now = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    title: "New chat",
    createdAt: now,
    updatedAt: now,
    knowledgeBaseId: "",
    documentId: null,
    topK: 5,
    messages: [],
  };
}

export function ChatProvider({ children }: Readonly<{ children: React.ReactNode }>) {
  const { user } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const hydratedRef = useRef(false);
  const key = user ? `rag.conversations.${user.id || user.email}` : "";

  useEffect(() => {
    hydratedRef.current = false;
    if (!key) return;
    try {
      const saved = localStorage.getItem(key);
      const parsed = saved ? JSON.parse(saved) as Conversation[] : [];
      const initial = Array.isArray(parsed) && parsed.length ? parsed : [newConversation()];
      setConversations(initial);
      setActiveId(initial[0].id);
    } catch {
      const initial = newConversation();
      setConversations([initial]);
      setActiveId(initial.id);
    } finally {
      hydratedRef.current = true;
    }
  }, [key]);

  useEffect(() => {
    if (!key || !hydratedRef.current) return;
    localStorage.setItem(key, JSON.stringify(conversations));
  }, [conversations, key]);

  const createConversation = useCallback(() => {
    const conversation = newConversation();
    setConversations((items) => [conversation, ...items]);
    setActiveId(conversation.id);
    return conversation.id;
  }, []);

  const selectConversation = useCallback((id: string) => setActiveId(id), []);

  const deleteConversation = useCallback((id: string) => {
    setConversations((items) => {
      const filtered = items.filter((item) => item.id !== id);
      if (!filtered.length) {
        const replacement = newConversation();
        setActiveId(replacement.id);
        return [replacement];
      }
      setActiveId((current) => current === id ? filtered[0].id : current);
      return filtered;
    });
  }, []);

  const appendMessage = useCallback((conversationId: string, message: ChatMessage) => {
    setConversations((items) => items.map((conversation) => {
      if (conversation.id !== conversationId) return conversation;
      const isFirstUserMessage = message.role === "user" && !conversation.messages.some((item) => item.role === "user");
      return {
        ...conversation,
        title: isFirstUserMessage ? shortTitle(message.content) : conversation.title,
        updatedAt: new Date().toISOString(),
        messages: [...conversation.messages, message],
      };
    }).sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)));
  }, []);

  const updateConversationSettings = useCallback((conversationId: string, settings: Partial<Pick<Conversation, "knowledgeBaseId" | "documentId" | "topK">>) => {
    setConversations((items) => items.map((conversation) => conversation.id === conversationId ? { ...conversation, ...settings, updatedAt: new Date().toISOString() } : conversation));
  }, []);

  const clearAll = useCallback(() => {
    const conversation = newConversation();
    setConversations([conversation]);
    setActiveId(conversation.id);
  }, []);

  const activeConversation = useMemo(() => conversations.find((item) => item.id === activeId) || conversations[0] || null, [activeId, conversations]);
  const value = useMemo(() => ({ conversations, activeConversation, activeId, createConversation, selectConversation, deleteConversation, appendMessage, updateConversationSettings, clearAll }), [activeConversation, activeId, appendMessage, clearAll, conversations, createConversation, deleteConversation, selectConversation, updateConversationSettings]);

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export function useChats() {
  const context = useContext(ChatContext);
  if (!context) throw new Error("useChats must be used inside ChatProvider");
  return context;
}
