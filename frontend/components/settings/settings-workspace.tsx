"use client";

import { useEffect, useState } from "react";
import { Activity, CheckCircle2, Database, ExternalLink, LoaderCircle, MessageSquareText, Server, ShieldCheck, Trash2, UserRound } from "lucide-react";
import { useAuth } from "@/components/providers/auth-provider";
import { useChats } from "@/components/providers/chat-provider";
import { useToast } from "@/components/providers/toast-provider";
import { API_BASE_URL, ApiError, buildHeaders, parseResponse } from "@/lib/api";
import { initials } from "@/lib/format";

interface HealthState { live: string; ready: string; database: string; redis: string }

export function SettingsWorkspace() {
  const { user } = useAuth();
  const { clearAll } = useChats();
  const { showToast } = useToast();
  const [health, setHealth] = useState<HealthState>({ live: "checking", ready: "checking", database: "checking", redis: "checking" });
  const [checking, setChecking] = useState(false);

  async function checkHealth() {
    setChecking(true);
    try {
      const liveResponse = await fetch(`${API_BASE_URL}/health/live`, { headers: buildHeaders() });
      const live = await parseResponse<Record<string, unknown>>(liveResponse);
      const readyResponse = await fetch(`${API_BASE_URL}/health/ready`, { headers: buildHeaders() });
      const ready = await parseResponse<Record<string, unknown>>(readyResponse);
      const checks = typeof ready.checks === "object" && ready.checks ? ready.checks as Record<string, { status?: string }> : {};
      setHealth({ live: String(live.status || "alive"), ready: String(ready.status || "ready"), database: checks.database?.status || "unknown", redis: checks.redis?.status || "unknown" });
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Health checks failed.";
      setHealth({ live: "unavailable", ready: "not_ready", database: "unknown", redis: "unknown" });
      showToast({ tone: "error", title: "Backend is not ready", description: message });
    } finally {
      setChecking(false);
    }
  }

  useEffect(() => { void checkHealth(); }, []);

  function clearHistory() {
    if (!confirm("Delete all locally stored conversations for this account?")) return;
    clearAll();
    showToast({ tone: "success", title: "Local chat history cleared" });
  }

  return <section className="page-workspace settings-page"><header className="page-header"><div><p className="eyebrow dark">Workspace preferences</p><h1>Settings</h1><p>Review your identity, backend connectivity, and browser-local data.</p></div></header><div className="settings-grid"><article className="settings-card profile-settings"><div className="settings-card-heading"><UserRound size={19} /><div><h2>Account</h2><p>Authenticated backend identity</p></div></div><div className="profile-panel"><div className="avatar profile-avatar">{initials(user?.full_name || "User")}</div><div><h3>{user?.full_name}</h3><p>{user?.email}</p><span className="role-chip"><ShieldCheck size={13} /> {user?.role}</span></div></div><dl className="detail-list"><div><dt>User ID</dt><dd>{user?.id}</dd></div><div><dt>Organization ID</dt><dd>{user?.organization_id}</dd></div><div><dt>Account status</dt><dd className="ok-text"><CheckCircle2 size={14} /> Active</dd></div></dl></article><article className="settings-card"><div className="settings-card-heading"><Activity size={19} /><div><h2>Backend health</h2><p>{API_BASE_URL}</p></div><button className="icon-button bordered" onClick={() => void checkHealth()}>{checking ? <LoaderCircle size={17} className="spin" /> : <Server size={17} />}</button></div><div className="health-list"><HealthRow icon={<Server size={17} />} label="API process" value={health.live} /><HealthRow icon={<Database size={17} />} label="MySQL" value={health.database} /><HealthRow icon={<Activity size={17} />} label="Redis" value={health.redis} /></div><a className="text-link" href={`${API_BASE_URL.replace(/\/api\/v1$/, "")}/docs`} target="_blank" rel="noreferrer">Open Swagger documentation <ExternalLink size={14} /></a></article><article className="settings-card"><div className="settings-card-heading"><MessageSquareText size={19} /><div><h2>Local conversation data</h2><p>Stored only in this browser</p></div></div><p className="settings-copy">The current backend does not yet store conversations. The sidebar history is saved in localStorage and is isolated by your user ID on this browser.</p><button className="danger-outline-button" onClick={clearHistory}><Trash2 size={16} /> Clear local chat history</button></article><article className="settings-card"><div className="settings-card-heading"><ShieldCheck size={19} /><div><h2>Session behavior</h2><p>Browser-tab token storage</p></div></div><p className="settings-copy">Access and refresh tokens are stored in sessionStorage. Closing the tab clears them. The client rotates refresh tokens whenever the backend returns an expired access-token response.</p></article></div></section>;
}

function HealthRow({ icon, label, value }: Readonly<{ icon: React.ReactNode; label: string; value: string }>) {
  const healthy = value === "ok" || value === "ready" || value === "alive";
  return <div className="health-row"><span>{icon}</span><strong>{label}</strong><em className={healthy ? "healthy" : "unhealthy"}>{value}</em></div>;
}
