import { useId } from "react";

/** ARIA's mark: an A whose crossbar is a spark, on the brand gradient (docs/logo-options). */
export function LogoMark({ size = 32 }: { size?: number }) {
  const gradient = useId();
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" style={{ display: "block", flexShrink: 0 }}>
      <defs>
        <linearGradient id={gradient} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#14b8a6" />
          <stop offset="0.5" stopColor="#0fa3a0" />
          <stop offset="1" stopColor="#7c6bf0" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="16" fill={`url(#${gradient})`} />
      <path d="M17 50 L32 13 L47 50" fill="none" stroke="#fff" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M32 29.5 C33.2 34.6 35.4 36.8 40.5 38 C35.4 39.2 33.2 41.4 32 46.5 C30.8 41.4 28.6 39.2 23.5 38 C28.6 36.8 30.8 34.6 32 29.5 Z" fill="#fff" />
    </svg>
  );
}
