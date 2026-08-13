import { api } from "./api";

const VAPID_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY ?? "";

export function pushAvailable(): boolean {
  if (typeof window === "undefined") return false;
  return Boolean(VAPID_PUBLIC_KEY) && "serviceWorker" in navigator && "PushManager" in window;
}

export async function isPushSubscribed(): Promise<boolean> {
  if (!pushAvailable()) return false;
  const registration = await registerServiceWorker();
  const subscription = await registration?.pushManager?.getSubscription();
  return Boolean(subscription);
}

export function urlBase64ToUint8Array(base64String: string): Uint8Array<ArrayBuffer> {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i += 1) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

export async function registerServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  if (!("serviceWorker" in navigator)) return null;
  try {
    return await navigator.serviceWorker.register("/sw.js");
  } catch {
    return null;
  }
}

export async function subscribeToPush(): Promise<boolean> {
  if (!VAPID_PUBLIC_KEY) return false;
  const registration = await registerServiceWorker();
  if (!registration) return false;
  if (!("pushManager" in registration)) return false;
  let subscription = await registration.pushManager.getSubscription();
  if (!subscription) {
    try {
      subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
      });
    } catch {
      return false;
    }
  }
  const raw = subscription.toJSON();
  if (!raw.endpoint || !raw.keys) return false;
  try {
    await api("/api/v1/push/subscribe", {
      method: "POST",
      body: JSON.stringify({
        endpoint: raw.endpoint,
        p256dh: raw.keys.p256dh,
        auth: raw.keys.auth,
      }),
    });
    return true;
  } catch {
    return false;
  }
}

export async function unsubscribeFromPush(): Promise<boolean> {
  const registration = await registerServiceWorker();
  const subscription = await registration?.pushManager?.getSubscription();
  if (subscription) {
    await subscription.unsubscribe();
    const raw = subscription.toJSON();
    if (raw.endpoint) {
      try {
        await api("/api/v1/push/unsubscribe", {
          method: "POST",
          body: JSON.stringify({
            endpoint: raw.endpoint,
            p256dh: raw.keys?.p256dh ?? "",
            auth: raw.keys?.auth ?? "",
          }),
        });
      } catch {
        // Server-side cleanup is best-effort.
      }
    }
  }
  return true;
}
