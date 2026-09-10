"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Building2, CircleAlert, LoaderCircle, Mail, Plus, RefreshCw, ShieldCheck, Trash2, UserRound, Users, X } from "lucide-react";
import { useAuth } from "@/components/providers/auth-provider";
import { useToast } from "@/components/providers/toast-provider";
import { ApiError, normalizeMembers, normalizeOrganization } from "@/lib/api";
import { formatDate, initials } from "@/lib/format";
import type { OrganizationInfo, OrganizationMember, OrganizationRole } from "@/lib/types";

export function MembersWorkspace() {
  const { apiFetch, user } = useAuth();
  const { showToast } = useToast();
  const [organization, setOrganization] = useState<OrganizationInfo | null>(null);
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const canManage = user?.role === "owner" || user?.role === "admin";

  async function load() {
    setLoading(true);
    try {
      const [organizationData, memberData] = await Promise.all([
        apiFetch<unknown>("/organizations/current"),
        apiFetch<unknown>("/organizations/current/members"),
      ]);
      setOrganization(normalizeOrganization(organizationData));
      setMembers(normalizeMembers(memberData));
    } catch (error) {
      showToast({ tone: "error", title: "Team data unavailable", description: error instanceof ApiError ? error.message : "Please try again." });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  async function updateRole(member: OrganizationMember, role: OrganizationRole) {
    setBusyId(member.membership_id);
    try {
      await apiFetch<unknown>(`/organizations/current/members/${encodeURIComponent(member.membership_id)}/role`, { method: "PATCH", body: JSON.stringify({ role }) });
      setMembers((items) => items.map((item) => item.membership_id === member.membership_id ? { ...item, role } : item));
      showToast({ tone: "success", title: "Role updated" });
    } catch (error) {
      showToast({ tone: "error", title: "Role update failed", description: error instanceof ApiError ? error.message : "Please try again." });
    } finally {
      setBusyId(null);
    }
  }

  async function deactivate(member: OrganizationMember) {
    if (!confirm(`Deactivate ${member.full_name}? They will no longer be able to sign in.`)) return;
    setBusyId(member.membership_id);
    try {
      await apiFetch<void>(`/organizations/current/members/${encodeURIComponent(member.membership_id)}`, { method: "DELETE" });
      setMembers((items) => items.map((item) => item.membership_id === member.membership_id ? { ...item, is_active: false } : item));
      showToast({ tone: "success", title: "Member deactivated" });
    } catch (error) {
      showToast({ tone: "error", title: "Deactivation failed", description: error instanceof ApiError ? error.message : "Please try again." });
    } finally {
      setBusyId(null);
    }
  }

  const activeCount = useMemo(() => members.filter((member) => member.is_active).length, [members]);

  return (
    <section className="page-workspace">
      <header className="page-header"><div><p className="eyebrow dark">Organization access</p><h1>Team</h1><p>Manage roles and active membership for your organization.</p></div>{canManage ? <button className="primary-button" onClick={() => setInviteOpen(true)}><Plus size={17} /> Add member</button> : null}</header>

      <div className="organization-card"><div className="organization-icon"><Building2 size={22} /></div><div><span>Current organization</span><strong>{organization?.name || "Loading…"}</strong><small>{organization?.slug || organization?.id}</small></div><div className="organization-role"><ShieldCheck size={15} /> {organization?.role || user?.role}</div></div>

      {!canManage ? <div className="inline-banner compact"><CircleAlert size={18} /><div><strong>Read-only team view</strong><p>Only owners and administrators can create, update, or deactivate members.</p></div></div> : null}

      <div className="toolbar-card team-toolbar"><div className="stat-inline"><Users size={17} /><span><strong>{activeCount}</strong> active members</span></div><button className="icon-button bordered" onClick={() => void load()} title="Refresh"><RefreshCw size={17} className={loading ? "spin" : ""} /></button></div>

      {loading ? <div className="table-loader"><LoaderCircle size={25} className="spin" /><p>Loading members…</p></div> : (
        <div className="member-grid">{members.map((member) => {
          const isCurrentUser = member.user_id === user?.id || member.email === user?.email;
          const protectedMember = member.role === "owner" || isCurrentUser || !member.is_active;
          return <article className={`member-card ${!member.is_active ? "inactive" : ""}`} key={member.membership_id}><div className="member-main"><div className="avatar large-avatar">{initials(member.full_name)}</div><div><div className="member-name-row"><h3>{member.full_name}</h3>{isCurrentUser ? <span>You</span> : null}{!member.is_active ? <span className="inactive-pill">Inactive</span> : null}</div><p><Mail size={14} /> {member.email}</p><small>Added {formatDate(member.created_at)}</small></div></div><div className="member-actions"><label><span>Role</span><select value={member.role} disabled={!canManage || protectedMember || busyId === member.membership_id} onChange={(event) => void updateRole(member, event.target.value as OrganizationRole)}><option value="owner" disabled>Owner</option>{user?.role === "owner" ? <option value="admin">Admin</option> : null}<option value="member">Member</option><option value="viewer">Viewer</option></select></label>{canManage && !protectedMember ? <button className="danger-text-button" disabled={busyId === member.membership_id} onClick={() => void deactivate(member)}>{busyId === member.membership_id ? <LoaderCircle size={16} className="spin" /> : <Trash2 size={16} />} Deactivate</button> : null}</div></article>;
        })}</div>
      )}

      {inviteOpen ? <InviteMemberModal ownerRole={user?.role || "member"} saving={saving} onClose={() => setInviteOpen(false)} onSubmit={async (payload) => { setSaving(true); try { await apiFetch<unknown>("/organizations/current/members", { method: "POST", body: JSON.stringify(payload) }); showToast({ tone: "success", title: "Member created", description: `${payload.email} can now sign in.` }); setInviteOpen(false); await load(); } catch (error) { showToast({ tone: "error", title: "Member creation failed", description: error instanceof ApiError ? error.message : "Please try again." }); } finally { setSaving(false); } }} /> : null}
    </section>
  );
}

function InviteMemberModal({ ownerRole, saving, onClose, onSubmit }: Readonly<{ ownerRole: OrganizationRole; saving: boolean; onClose: () => void; onSubmit: (payload: { email: string; full_name: string; password: string; role: OrganizationRole }) => Promise<void> }>) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<OrganizationRole>("member");

  function submit(event: FormEvent) {
    event.preventDefault();
    void onSubmit({ full_name: fullName.trim(), email: email.trim(), password, role });
  }

  return <div className="modal-layer"><button className="modal-backdrop" onClick={onClose} aria-label="Close dialog" /><form className="modal-card" onSubmit={submit}><div className="modal-header"><div><h2>Add organization member</h2><p>Create an account and assign its initial role.</p></div><button className="icon-button" type="button" onClick={onClose}><X size={19} /></button></div><div className="modal-body form-stack"><label className="field-label">Full name<input className="text-input" value={fullName} onChange={(event) => setFullName(event.target.value)} required minLength={2} /></label><label className="field-label">Email<input className="text-input" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label><label className="field-label">Temporary password<input className="text-input" type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={12} maxLength={128} required /></label><label className="field-label">Role<select className="text-input" value={role} onChange={(event) => setRole(event.target.value as OrganizationRole)}>{ownerRole === "owner" ? <option value="admin">Admin</option> : null}<option value="member">Member</option><option value="viewer">Viewer</option></select></label></div><div className="modal-footer"><button className="secondary-button" type="button" onClick={onClose}>Cancel</button><button className="primary-button" type="submit" disabled={saving}>{saving ? <><LoaderCircle size={17} className="spin" /> Creating…</> : <><UserRound size={17} /> Create member</>}</button></div></form></div>;
}
