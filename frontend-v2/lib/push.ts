const VAPID_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY ?? "";
const SW_PATH = "/sw.js";

export function pushSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window &&
    VAPID_PUBLIC_KEY !== ""
  );
}

/** Register the service worker; returns null when unsupported or registration fails. */
export async function registerServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  if (typeof window === "undefined" || !("serviceWorker" in navigator)) return null;
  try {
    return await navigator.serviceWorker.register(SW_PATH);
  } catch {
    return null;
  }
}

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = window.atob(base64);
  const output = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) output[i] = raw.charCodeAt(i);
  return output;
}

export type EnablePushResult =
  | { status: "subscribed" }
  | { status: "permission-denied" }
  | { status: "unsupported" }
  | { status: "error"; message: string };

/**
 * Full browser push enable flow: permission -> service worker -> subscription
 * -> POST /push/subscribe. The caller persists the notify_push preference.
 */
export async function enablePush(
  subscribeApi: (payload: { endpoint: string; p256dh: string; auth: string }) => Promise<unknown>,
): Promise<EnablePushResult> {
  if (!pushSupported()) return { status: "unsupported" };
  const permission = await Notification.requestPermission();
  if (permission !== "granted") return { status: "permission-denied" };
  const registration = await registerServiceWorker();
  if (!registration) return { status: "error", message: "Service worker unavailable" };
  try {
    const existing = await registration.pushManager.getSubscription();
    const sub =
      existing ??
      (await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY).buffer as ArrayBuffer,
      }));
    const json = sub.toJSON() as { endpoint?: string; keys?: { p256dh?: string; auth?: string } };
    if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) {
      return { status: "error", message: "Incomplete push subscription" };
    }
    await subscribeApi({ endpoint: json.endpoint, p256dh: json.keys.p256dh, auth: json.keys.auth });
    return { status: "subscribed" };
  } catch (e) {
    return { status: "error", message: e instanceof Error ? e.message : "Push subscription failed" };
  }
}

/**
 * Browser-side teardown for push: unsubscribe the active subscription and tell
 * the backend to drop it. Best-effort; resolves false when nothing was removed.
 */
export async function disablePush(
  unsubscribeApi: (endpoint: string) => Promise<unknown>,
): Promise<boolean> {
  if (typeof window === "undefined" || !("serviceWorker" in navigator)) return false;
  try {
    const registration = await navigator.serviceWorker.getRegistration(SW_PATH);
    const sub = (await registration?.pushManager.getSubscription()) ?? null;
    if (!sub) return false;
    const endpoint = sub.endpoint;
    await sub.unsubscribe();
    await unsubscribeApi(endpoint);
    return true;
  } catch {
    return false;
  }
}