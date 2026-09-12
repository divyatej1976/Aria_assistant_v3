"use client";

import { Icon } from "@/components/icons";

export function toast(msg: string) {
  if (typeof window === "undefined") return;
  let wrap = document.getElementById("toasts");
  if (!wrap) {
    wrap = document.createElement("div");
    wrap.id = "toasts";
    document.body.appendChild(wrap);
  }
  const el = document.createElement("div");
  el.className = "toast";
  el.style.display = "flex";
  el.style.gap = "12px";
  const svgHost = document.createElement("span");
  svgHost.style.display = "inline-flex";
  const span = document.createElement("span");
  span.textContent = msg;
  el.append(svgHost, span);
  wrap.appendChild(el);
  // Per-toast removal: each element owns its timer, so a newer toast can
  // never strand an older one in the DOM.
  const interval = window.setInterval(() => {
    el.remove();
    window.clearInterval(interval);
  }, 2600);
}

export function ToastSvg() {
  return <Icon name="check" size={18} />;
}
