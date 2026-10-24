import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { PaletteProvider } from "@/components/palette-provider";
import { AmbientBackground } from "@/components/ambient-background";
import { AuthProvider } from "@/components/auth-provider";
import { ErrorMonitor } from "@/components/error-monitor";
import { ActiveContextProvider } from "@/components/use-active-context";
import { MotionProvider } from "@/components/motion-system";

// Self-hosted variable fonts: production builds must not depend on Google's CDN.
const jakarta = localFont({
  src: "./fonts/plus-jakarta-sans-latin-var.woff2",
  variable: "--font-aria-sans",
  display: "swap",
});

const jetbrains = localFont({
  src: "./fonts/jetbrains-mono-latin-var.woff2",
  variable: "--font-aria-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ARIA — AI-Powered Personalized Learning System",
  description:
    "Your AI companion for your entire learning journey. Learn, assess, plan, listen, create and track.",
  // Home-screen app on iPhone (Android reads app/manifest.ts).
  appleWebApp: { capable: true, title: "ARIA", statusBarStyle: "default" },
  icons: { apple: "/apple-touch-icon.png" },
};

export const viewport: Viewport = {
  themeColor: "#0fa3a0",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${jakarta.variable} ${jetbrains.variable}`} data-theme="aurora" data-scroll-behavior="smooth" suppressHydrationWarning>
      <body className="antialiased">
        <PaletteProvider>
          <AuthProvider>
            <ErrorMonitor />
          <ActiveContextProvider>
            <MotionProvider>
            <AmbientBackground />
            {children}
            </MotionProvider>
          </ActiveContextProvider>
        </AuthProvider>
        </PaletteProvider>
      </body>
    </html>
  );
}
