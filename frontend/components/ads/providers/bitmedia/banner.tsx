"use client";

import { useEffect, useRef } from "react";

const BITMEDIA_CDN = "cdn.bmcdn6.com";

function safeToken(value: string) {
  return /^[a-zA-Z0-9_-]+$/.test(value) ? value : "";
}

export function BitmediaPlacement() {
  const placementId = safeToken(process.env.NEXT_PUBLIC_BITMEDIA_PLACEMENT_ID?.trim() || "");
  const enabled = process.env.NEXT_PUBLIC_BITMEDIA_ENABLED?.toLowerCase() === "true";
  const width = Number.parseInt(process.env.NEXT_PUBLIC_BITMEDIA_WIDTH || "970", 10) || 970;
  const height = Number.parseInt(process.env.NEXT_PUBLIC_BITMEDIA_HEIGHT || "90", 10) || 90;
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!enabled || !placementId || !container) return;

    const ad = document.createElement("ins");
    ad.className = placementId;
    ad.style.display = "inline-block";
    ad.style.width = `${width}px`;
    ad.style.height = `${height}px`;
    container.appendChild(ad);

    const script = document.createElement("script");
    script.async = true;
    script.src = `https://${BITMEDIA_CDN}/js/${placementId}.js?v=${Date.now()}`;
    document.head.appendChild(script);

    return () => {
      script.remove();
      container.replaceChildren();
    };
  }, [enabled, height, placementId, width]);

  if (!enabled || !placementId) return null;

  return (
    <section aria-label="Bitmedia sponsored advertisement" className="ad-provider ad-provider-bitmedia">
      <p>Sponsored</p>
      <div ref={containerRef} style={{ maxWidth: "100%", overflow: "auto" }} />
    </section>
  );
}
