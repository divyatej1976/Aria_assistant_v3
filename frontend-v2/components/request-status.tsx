"use client";

import { useEffect, useState } from "react";

export function RequestStatus({ label }: { label: string }) {
  const [longWait, setLongWait] = useState(false);
  useEffect(() => {
    const timer = window.setTimeout(() => setLongWait(true), 8000);
    return () => window.clearTimeout(timer);
  }, []);
  return <div className="request-status" role="status" aria-live="polite">
    <b>{longWait ? "Still working…" : label}</b>
    <p>{longWait ? "Longer answers can take a moment. Keep this page open." : "Preparing your next step."}</p>
    <div className="request-lines" aria-hidden="true"><span /><span /><span /></div>
  </div>;
}
