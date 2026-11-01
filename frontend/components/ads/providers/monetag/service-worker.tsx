"use client";

import { useEffect } from "react";

export function MonetagServiceWorkerCleanup() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;

    const workerUrl = new URL("/sw.js", window.location.origin).href;
    void navigator.serviceWorker
      .getRegistrations()
      .then((registrations) =>
        Promise.all(
          registrations
            .filter((registration) =>
              [registration.active, registration.waiting, registration.installing].some(
                (worker) => worker?.scriptURL === workerUrl,
              ),
            )
            .map((registration) => registration.unregister()),
        ),
      )
      .catch((error: unknown) => {
        console.error("Monetag service worker could not be unregistered.", error);
      });
  }, []);

  return null;
}
