"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Menu } from "lucide-react";
import { useAuth } from "@/components/providers/auth-provider";
import { Sidebar } from "@/components/layout/sidebar";

export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const { loading, isAuthenticated } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (!loading && !isAuthenticated) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [isAuthenticated, loading, pathname, router]);

  useEffect(() => setMobileOpen(false), [pathname]);

  if (loading || !isAuthenticated) {
    return <div className="full-loader"><div className="brand-mark pulse"><span className="spinner" /></div><p>Opening your workspace…</p></div>;
  }

  return (
    <div className="app-frame">
      <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
      {mobileOpen ? <button className="mobile-backdrop" aria-label="Close navigation" onClick={() => setMobileOpen(false)} /> : null}
      <main className="app-main">
        <button className="mobile-menu-button" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu size={20} /></button>
        {children}
      </main>
    </div>
  );
}
