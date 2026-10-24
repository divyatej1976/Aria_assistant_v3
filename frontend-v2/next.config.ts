import type { NextConfig } from "next";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' data: https://fonts.gstatic.com",
  // Tutor answers may embed diagrams from Wikimedia only (see IMAGE_HOSTS in tutor-markdown.tsx).
  "img-src 'self' data: blob: https://upload.wikimedia.org",
  "media-src 'self' blob: data:",
  // Error reports go to Sentry (components/error-monitor.tsx) when it is configured.
  `connect-src 'self' ${API_URL} https://*.ingest.sentry.io https://*.ingest.us.sentry.io https://*.ingest.de.sentry.io`,
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join("; ");

const nextConfig: NextConfig = {
  distDir: process.env.ARIA_NEXT_DIST_DIR ?? ".next",
  poweredByHeader: false,
  // The phone tab bar and top bar fill every corner; Next.js still reports
  // compile and runtime errors without the badge.
  devIndicators: false,
  // On Vercel the API runs elsewhere (a Hugging Face Space). Forwarding /api keeps the site and API
  // on one origin, so the sign-in cookies stay first-party. Set ARIA_API_PROXY to the API's URL.
  async rewrites() {
    const target = process.env.ARIA_API_PROXY;
    return target ? [{ source: "/api/:path*", destination: `${target}/api/:path*` }] : [];
  },
  async headers() {
    const headers = [
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "X-Frame-Options", value: "DENY" },
      { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
      { key: "Permissions-Policy", value: "camera=(self), microphone=(self), geolocation=()" },
      { key: "Content-Security-Policy", value: CSP },
    ];
    if (process.env.NODE_ENV === "production") {
      headers.push({
        key: "Strict-Transport-Security",
        value: "max-age=63072000; includeSubDomains; preload",
      });
    }
    return [
      {
        source: "/:path*",
        headers,
      },
    ];
  },
};

export default nextConfig;
