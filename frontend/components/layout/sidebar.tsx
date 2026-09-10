"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { BookOpenText, FileText, LogOut, MessageSquareText, Moon, MoreHorizontal, Plus, Search, Settings, Sparkles, Sun, Trash2, Users, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/components/providers/auth-provider";
import { useChats } from "@/components/providers/chat-provider";
import { initials } from "@/lib/format";

export function Sidebar({ mobileOpen, onClose }: Readonly<{ mobileOpen: boolean; onClose: () => void }>) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const { conversations, activeId, createConversation, selectConversation, deleteConversation } = useChats();
  const [query, setQuery] = useState("");
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [openMenu, setOpenMenu] = useState<string | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem("rag.theme");
    const selected = saved === "dark" ? "dark" : "light";
    setTheme(selected);
    document.documentElement.dataset.theme = selected;
  }, []);

  const filtered = useMemo(() => conversations.filter((item) => item.title.toLowerCase().includes(query.toLowerCase())), [conversations, query]);

  function toggleTheme() {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    document.documentElement.dataset.theme = next;
    localStorage.setItem("rag.theme", next);
  }

  function newChat() {
    createConversation();
    router.push("/chat");
    onClose();
  }

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  const nav = [
    { href: "/chat", label: "Chat", icon: MessageSquareText },
    { href: "/documents", label: "Documents", icon: FileText },
    { href: "/members", label: "Team", icon: Users },
    { href: "/settings", label: "Settings", icon: Settings },
  ];

  return (
    <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
      <div className="sidebar-top">
        <Link href="/chat" className="sidebar-brand" onClick={onClose}>
          <span className="brand-mark"><Sparkles size={18} /></span>
          <span><strong>{process.env.NEXT_PUBLIC_APP_NAME || "Knowledge Chat"}</strong><small>Grounded document AI</small></span>
        </Link>
        <button className="sidebar-close" onClick={onClose} aria-label="Close navigation"><X size={19} /></button>
      </div>

      <button className="new-chat-button" onClick={newChat}><Plus size={18} /> New chat</button>

      <nav className="sidebar-nav" aria-label="Main navigation">
        {nav.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href;
          return <Link key={item.href} href={item.href} className={active ? "nav-link active" : "nav-link"} onClick={onClose}><Icon size={18} /><span>{item.label}</span></Link>;
        })}
      </nav>

      <div className="sidebar-divider" />
      <div className="sidebar-section-heading"><span>Recent</span><BookOpenText size={15} /></div>
      <label className="sidebar-search"><Search size={15} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search chats" /></label>

      <div className="conversation-list">
        {filtered.map((conversation) => (
          <div className={`conversation-row ${pathname === "/chat" && activeId === conversation.id ? "active" : ""}`} key={conversation.id}>
            <button className="conversation-main" onClick={() => { selectConversation(conversation.id); router.push("/chat"); onClose(); }}>
              <MessageSquareText size={15} />
              <span>{conversation.title}</span>
            </button>
            <button className="conversation-menu-trigger" onClick={() => setOpenMenu((current) => current === conversation.id ? null : conversation.id)} aria-label="Conversation options"><MoreHorizontal size={16} /></button>
            {openMenu === conversation.id ? (
              <div className="conversation-menu">
                <button onClick={() => { deleteConversation(conversation.id); setOpenMenu(null); }}><Trash2 size={15} /> Delete</button>
              </div>
            ) : null}
          </div>
        ))}
        {!filtered.length ? <p className="sidebar-empty">No matching chats</p> : null}
      </div>

      <div className="sidebar-footer">
        <button className="theme-button" onClick={toggleTheme}>{theme === "light" ? <Moon size={17} /> : <Sun size={17} />} {theme === "light" ? "Dark mode" : "Light mode"}</button>
        <div className="user-card">
          <div className="avatar">{initials(user?.full_name || user?.email || "User")}</div>
          <div className="user-card-text"><strong>{user?.full_name || "User"}</strong><span>{user?.role}</span></div>
          <button onClick={handleLogout} aria-label="Sign out" title="Sign out"><LogOut size={17} /></button>
        </div>
      </div>
    </aside>
  );
}
