// Same rules as the server (backend/app/schemas/auth.py): a real-looking email, and new
// passwords of 8+ characters with a letter, a number and a symbol.
export const emailOk = (email: string) => /^[^@\s]+@[^@\s]+\.[a-z]{2,}$/i.test(email.trim());

const RULES: [string, (p: string) => boolean][] = [
  ["8+ characters", (p) => p.length >= 8],
  ["a letter", (p) => /[A-Za-z]/.test(p)],
  ["a number", (p) => /\d/.test(p)],
  ["a symbol (like ! or -)", (p) => /[^A-Za-z0-9]/.test(p)],
];

export const passwordOk = (password: string) => RULES.every(([, test]) => test(password));

export function PasswordRules({ value }: { value: string }) {
  return (
    <ul aria-label="What it needs" style={{ listStyle: "none", padding: 0, margin: "6px 0 0", display: "flex", flexWrap: "wrap", gap: "4px 12px", fontSize: 12 }}>
      {RULES.map(([label, test]) => {
        const met = test(value);
        return (
          <li key={label} style={{ color: met ? "var(--success, #16a34a)" : "var(--text-3)", fontWeight: met ? 600 : 400 }}>
            {met ? "✓" : "○"} {label}
          </li>
        );
      })}
    </ul>
  );
}
