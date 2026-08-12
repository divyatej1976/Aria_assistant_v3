import { FlatCompat } from "@eslint/eslintrc";
import { dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({ baseDirectory: __dirname });

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    ignores: [".next/**", "node_modules/**", "e2e/**", "next-env.d.ts"],
  },
  {
    rules: {
      // Plus Jakarta Sans + Material Symbols are intentionally loaded via <link>
      // (next/font cannot load Material Symbols).
      "@next/next/no-page-custom-font": "off",
    },
  },
];

export default eslintConfig;
