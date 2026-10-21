"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeHighlight from "rehype-highlight";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { normalizeMath } from "@/lib/normalize-math";

// Must match img-src in next.config.ts; other hosts become a plain link.
export const IMAGE_HOSTS = ["upload.wikimedia.org"];

function allowedImage(src: unknown): src is string {
  try {
    const url = new URL(String(src));
    return url.protocol === "https:" && IMAGE_HOSTS.includes(url.hostname);
  } catch {
    return false;
  }
}

/** Renders tutor markdown with GFM tables, math, highlighted code, and copy buttons. */
export function TutorMarkdown({ content }: { content: string }) {
  return (
    <div className="tutor-md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeKatex, { throwOnError: false }], rehypeHighlight]}
        components={{
          pre: ({ children, ...props }) => (
            <div className="code-block">
              <button
                type="button"
                className="code-copy"
                onClick={(e) => {
                  const pre = (e.currentTarget.parentElement as HTMLElement).querySelector("pre");
                  const text = pre?.textContent ?? "";
                  void navigator.clipboard?.writeText(text);
                  e.currentTarget.textContent = "Copied!";
                  window.setTimeout(() => {
                    e.currentTarget.textContent = "Copy";
                  }, 1500);
                }}
              >
                Copy
              </button>
              <pre {...props}>{children}</pre>
            </div>
          ),
          a: ({ children: kids, ...props }) => (
            <a {...props} target="_blank" rel="noreferrer noopener">
              {kids}
            </a>
          ),
          img: ({ src, alt }) =>
            allowedImage(src) ? (
              <figure className="tutor-figure">
                {/* eslint-disable-next-line @next/next/no-img-element -- remote, unknown size */}
                <img src={src} alt={alt ?? ""} loading="lazy" referrerPolicy="no-referrer" />
                {alt && <figcaption>{alt}</figcaption>}
              </figure>
            ) : typeof src === "string" && /^https?:/.test(src) ? (
              <a href={src} target="_blank" rel="noreferrer noopener">{alt || "Open image"}</a>
            ) : (
              <>{alt}</>
            ),
        }}
      >
        {normalizeMath(content)}
      </ReactMarkdown>
    </div>
  );
}
