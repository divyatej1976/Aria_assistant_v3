import type { MetadataRoute } from "next";

/** Makes ARIA installable ("Add to Home screen"): opens full-screen on the dashboard with the spark icon. */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "ARIA: AI study companion",
    short_name: "ARIA",
    description: "Learn, practise, plan and listen with your AI tutor.",
    start_url: "/app",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#edf1f7",
    theme_color: "#0fa3a0",
    categories: ["education", "productivity"],
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
