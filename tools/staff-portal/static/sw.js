/* Staff portal service worker: installs the portal as an app and shows staff alerts.
   Pushes carry no data (nothing about players passes through the browser's push service): on a push the worker asks the
   portal for the newest alert, with the staff member's own sign-in, and shows that. Pages are never cached. */
"use strict";
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {});   // online only: every request goes to the portal as usual

self.addEventListener("push", (e) => {
  e.waitUntil((async () => {
    let a = null;
    try {
      const r = await fetch("/api/push/latest", { credentials: "same-origin", cache: "no-store" });
      if (r.ok) a = (await r.json()).alert;
    } catch (err) { a = null; }
    const title = a ? a.title : "New staff alert";
    return self.registration.showNotification(title, {
      body: a ? a.body : "Open the staff portal to see it.", tag: a ? "alert-" + a.id : "alert",
      icon: "/static/icon-192.png", badge: "/static/favicon.png", data: { url: a ? a.url : "/#/alerts" },
    });
  })());
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || "/#/home";
  e.waitUntil((async () => {
    const all = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const c of all) { if ("focus" in c) { await c.navigate(url).catch(() => {}); return c.focus(); } }
    return self.clients.openWindow(url);
  })());
});
