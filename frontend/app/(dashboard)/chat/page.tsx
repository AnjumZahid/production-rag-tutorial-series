import type { Metadata } from "next";
import { ChatWorkspace } from "@/components/chat/chat-workspace";

export const metadata: Metadata = { title: "Chat" };

export default function ChatPage() {
  return <ChatWorkspace />;
}
