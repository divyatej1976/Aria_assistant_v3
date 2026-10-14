"use client";

import { Icon } from "./icons";
import { usePageVisible } from "./motion-system";

export function ResourceProcessing({ kind }: { kind: "file" | "text" }) {
  const visible = usePageVisible();
  return <div className="resource-processing" role="status"><div className="resource-processing-art" aria-hidden="true" style={{ animationPlayState: visible ? "running" : "paused" }}><Icon name="file" size={24} /><span /><span /><span /></div><div><strong>{kind === "file" ? "Uploading and processing your material" : "Processing your study text"}</strong><p>ARIA is preparing the content for learning. This may take a moment.</p></div></div>;
}
