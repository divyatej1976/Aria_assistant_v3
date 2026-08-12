import { AuthGuard } from "../../components/auth-guard";
import { AuthProvider } from "../../components/auth-provider";

export default function OnboardingLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <AuthProvider>
      <AuthGuard>{children}</AuthGuard>
    </AuthProvider>
  );
}
