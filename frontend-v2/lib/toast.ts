"use client";

const CHECK_SVG =
  '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--success);flex-shrink:0"><path d="M20 6 9 17l-5-5"/></svg>';

const observers = new WeakMap<HTMLElement, MutationObserver>();

export function toast(msg: string, kind: "success" | "error" | "info" = "info") {
  if (typeof window === "undefined") return;
  const host = Array.from(document.querySelectorAll("dialog[open]")).at(-1) ?? document.body;
  let wrap = document.getElementById("toasts");
  if (!wrap) {
    wrap = document.createElement("div");
    wrap.id = "toasts";
    const container = wrap;
    const observer = new MutationObserver(() => {
      if (!container.childElementCount) return;
      const currentHost = Array.from(document.querySelectorAll("dialog[open]")).at(-1) ?? document.body;
      if (container.parentElement !== currentHost) currentHost.appendChild(container);
    });
    observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["open"] });
    observers.set(container, observer);
  }
  // Native dialogs occupy the browser's top layer; a body z-index cannot
  // place feedback above them. Keep feedback inside the active dialog.
  host.appendChild(wrap);
  const el = document.createElement("div");
  el.className = "toast";
  el.setAttribute("role", kind === "error" ? "alert" : "status");
  el.setAttribute("aria-atomic", "true");
  el.style.display = "flex";
  el.style.alignItems = "center";
  el.style.gap = "12px";
  const icon = document.createElement("span");
  icon.setAttribute("aria-hidden", "true");
  if (kind === "success") icon.innerHTML = CHECK_SVG;
  else {
    icon.textContent = kind === "error" ? "!" : "i";
    icon.style.color = kind === "error" ? "var(--danger-strong)" : "var(--accent)";
  }
  icon.style.display = "inline-flex";
  icon.style.flexShrink = "0";
  const text = document.createElement("span");
  text.textContent = msg;
  el.append(icon, text);
  const dismiss = document.createElement("button");
  dismiss.type = "button";
  dismiss.className = "toast-dismiss";
  dismiss.setAttribute("aria-label", "Dismiss notification");
  dismiss.textContent = "×";
  const remove = () => {
    window.clearTimeout(timer);
    el.remove();
    if (wrap?.childElementCount === 0) {
      observers.get(wrap)?.disconnect();
      observers.delete(wrap);
      wrap.remove();
    }
  };
  dismiss.addEventListener("click", remove);
  el.appendChild(dismiss);
  wrap.appendChild(el);
  let timer = window.setTimeout(remove, kind === "error" ? 8000 : 3000);
  el.addEventListener("mouseenter", () => window.clearTimeout(timer));
  el.addEventListener("focusin", () => window.clearTimeout(timer));
  const resume = () => {
    if (!el.matches(":hover, :focus-within")) {
      window.clearTimeout(timer);
      timer = window.setTimeout(remove, kind === "error" ? 8000 : 3000);
    }
  };
  el.addEventListener("mouseleave", resume);
  el.addEventListener("focusout", resume);
}
