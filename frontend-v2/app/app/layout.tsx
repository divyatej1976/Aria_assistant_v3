import { AppShell } from "@/components/app-shell";
import { ContextGuard } from "@/components/context-guard";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppShell>
      <ContextGuard>{children}</ContextGuard>
    </AppShell>
  );
}
