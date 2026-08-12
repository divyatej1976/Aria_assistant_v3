import { AppShell } from "../../components/app-shell";
import { AuthGuard } from "../../components/auth-guard";
import { AuthProvider } from "../../components/auth-provider";

export default function AppLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <AuthProvider>
      <AuthGuard>
        <AppShell>{children}</AppShell>
      </AuthGuard>
    </AuthProvider>
  );
}
