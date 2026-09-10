import { AppShell } from "@/components/layout/app-shell";
import { ChatProvider } from "@/components/providers/chat-provider";

export default function DashboardLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <ChatProvider>
      <AppShell>{children}</AppShell>
    </ChatProvider>
  );
}
