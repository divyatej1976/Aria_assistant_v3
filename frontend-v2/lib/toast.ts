"use client";

let counter = 0;

const CHECK_SVG =
  '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--success);flex-shrink:0"><path d="M20 6 9 17l-5-5"/></svg>';

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
  el.style.alignItems = "center";
  el.style.gap = "12px";
  el.innerHTML = CHECK_SVG + "<span>" + msg + "</span>";
  wrap.appendChild(el);
  counter += 1;
  const id = counter;
  const interval = window.setInterval(() => {
    if (id !== counter) return;
    el.remove();
    window.clearInterval(interval);
  }, 2600);
}
