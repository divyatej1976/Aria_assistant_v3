/** Models write \[..\], \(..\) or a bare "[ ..\frac.. ]" line; remark-math only
 * reads $ delimiters. Code spans and fences are left untouched. */
export function normalizeMath(content: string): string {
  return content
    .split(/(```[\s\S]*?(?:```|$)|`[^`\n]*`)/)
    .map((part, i) =>
      i % 2
        ? part
        : part
            .replace(/\\\[([\s\S]+?)\\\]/g, (_, m) => `\n$$\n${m.trim()}\n$$\n`)
            .replace(/\\\(([\s\S]+?)\\\)/g, (_, m) => `$${m.trim()}$`)
            .replace(/^[ \t]*\[\s+(.*\\[a-zA-Z].*?)\s+\][ \t]*$/gm, (_, m) => `$$\n${m}\n$$`),
    )
    .join("");
}
