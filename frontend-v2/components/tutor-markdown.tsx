"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";

/** Renders tutor markdown with GFM tables, highlighted code, and copy buttons. */
export function TutorMarkdown({ content }: { content: string }) {
  return (
    <div className="tutor-md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
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
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}