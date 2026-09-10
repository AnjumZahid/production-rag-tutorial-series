import type { Metadata } from "next";
import { MembersWorkspace } from "@/components/members/members-workspace";

export const metadata: Metadata = { title: "Team" };

export default function MembersPage() {
  return <MembersWorkspace />;
}
