// Run: node tests/normalize-math.check.mts
import assert from "node:assert";
import { createElement as h } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
// @ts-expect-error -- Node strips types and needs the .ts extension
import { normalizeMath } from "../lib/normalize-math.ts";
const render = (s: string) => renderToStaticMarkup(h(ReactMarkdown, { remarkPlugins: [remarkMath], rehypePlugins: [rehypeKatex] }, normalizeMath(s)));
for (const src of [
  String.raw`\[ P(\text{event}) = \frac{\text{Number of favorable outcomes}}{\text{Total number of outcomes}} \]`,
  String.raw`[ P(\text{event}) = \frac{a}{b} ]`,
  String.raw`So \( x^2 \) grows and $y$ too.`,
]) assert.match(render(src), /class="katex/, src);
const code = String.raw`${"`"}\(a\)${"`"} and ${"```"}
\[b\]
${"```"}`;
assert.equal(normalizeMath(code), code);
assert.equal(normalizeMath("see [the docs](http://x)"), "see [the docs](http://x)");
console.log("ok");
