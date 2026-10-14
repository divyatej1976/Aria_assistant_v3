// Tailwind CSS v4 + Next.js 16 (Turbopack).
//
// IMPORTANT: keep the plugin as an OBJECT-LITERAL entry. Importing the plugin
// directly (`import tailwindcss from "@tailwindcss/postcss"; plugins: [tailwindcss()]`)
// fails the production build with "non-ecmascript placeable asset" because
// Turbopack's PostCSS bridge tries to place the plugin's native addons
// (@tailwindcss/oxide, lightningcss) as assets. The object form resolves the
// plugin by name without triggering that path and builds cleanly.
const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

export default config;