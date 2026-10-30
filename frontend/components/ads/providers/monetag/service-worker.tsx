"use client";

import { useEffect } from "react";

export function MonetagServiceWorker() {
  const enabled = process.env.NEXT_PUBLIC_MONETAG_ENABLED?.toLowerCase() === "true";

  useEffect(() => {
    if (!enabled || !("serviceWorker" in navigator)) return;

    void navigator.serviceWorker.register("/sw.js").catch((error: unknown) => {
      console.error("Monetag service worker could not be registered.", error);
    });
  }, [enabled]);

  return null;
}
