self.addEventListener("push", (event) => {
  let title = "ARIA";
  let body = "";
  if (event.data) {
    try {
      const data = event.data.json();
      title = data.title || title;
      body = data.body || "";
    } catch {
      body = event.data.text() || "";
    }
  }
  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      tag: "aria-notification",
      renotify: false,
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if ("focus" in client) return client.focus();
      }
      return self.clients.openWindow("/app");
    }),
  );
});
