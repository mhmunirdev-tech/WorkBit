"use client";

import { useEffect, useRef } from "react";

const COINZILLA_SCRIPT = "https://coinzillatag.com/lib/wdnative.js";

declare global {
  interface Window {
    czilla_widget?: Array<Record<string, unknown>>;
  }
}

export function CoinzillaNativePlacement() {
  const zoneId = process.env.NEXT_PUBLIC_COINZILLA_ZONE_ID?.trim();
  const enabled = process.env.NEXT_PUBLIC_COINZILLA_ENABLED?.toLowerCase() === "true";
  const containerRef = useRef<HTMLDivElement>(null);
  const containerId = zoneId ? `c_widget_${zoneId}` : "coinzilla-widget";

  useEffect(() => {
    if (!enabled || !zoneId || !containerRef.current) return;

    const script = document.createElement("script");
    script.src = COINZILLA_SCRIPT;
    script.async = false;
    script.onload = () => {
      const queue = window.czilla_widget ?? [];
      queue.push({ zone: zoneId, article: true, mobile: true });
      window.czilla_widget = queue;
    };
    document.head.appendChild(script);

    return () => script.remove();
  }, [enabled, zoneId]);

  if (!enabled || !zoneId) return null;

  return (
    <section aria-label="Coinzilla sponsored advertisement" className="ad-provider ad-provider-coinzilla">
      <p>Sponsored</p>
      <div id={containerId} ref={containerRef} />
    </section>
  );
}
