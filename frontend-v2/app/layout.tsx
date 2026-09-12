import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { PaletteProvider } from "@/components/palette-provider";
import { AmbientBackground } from "@/components/ambient-background";
import { AuthProvider } from "@/components/auth-provider";
import { ActiveContextProvider } from "@/components/use-active-context";

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
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-theme="aurora" suppressHydrationWarning>
      <body className={`${jakarta.variable} ${jetbrains.variable} antialiased`}>
        <PaletteProvider>
          <AuthProvider>
          <ActiveContextProvider>
            <AmbientBackground />
            {children}
          </ActiveContextProvider>
        </AuthProvider>
        </PaletteProvider>
      </body>
    </html>
  );
}
