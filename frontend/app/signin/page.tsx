import { AuthForm } from "../../components/auth-form";
import { ThemeToggle } from "../../components/theme-toggle";

export default function SigninPage() {
  return (
    <main className="min-h-screen bg-background flex items-center justify-center p-4 sm:p-container-padding">
      <div className="fixed top-4 right-4">
        <ThemeToggle />
      </div>
      <AuthForm mode="signin" />
    </main>
  );
}
