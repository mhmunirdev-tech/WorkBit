"use client";

import { useEffect, useRef } from "react";

const BANNER_SCRIPT_URL = "https://offerwall.me/api/public/banner-code.js";
const BANNER_FRAME_ORIGIN = "https://offerwall.me";

export function OfferwallMeBannerPlacement() {
  const containerRef = useRef<HTMLDivElement>(null);
  const enabled =
    process.env.NEXT_PUBLIC_OFFERWALL_ME_BANNER_ENABLED?.toLowerCase() === "true";
  const placementId =
    process.env.NEXT_PUBLIC_OFFERWALL_ME_BANNER_PLACEMENT_ID?.trim();

  useEffect(() => {
    const container = containerRef.current;
    if (!enabled || !placementId || !container) return;

    const desktop = window.matchMedia("(min-width: 1024px)");
    let script: HTMLScriptElement | undefined;

    const loadBanner = () => {
      script?.remove();
      container.replaceChildren();

      const width = desktop.matches ? 728 : 300;
      const height = desktop.matches ? 90 : 250;
      container.style.width = `${width}px`;
      container.style.height = `${height}px`;

      script = document.createElement("script");
      script.async = true;
      script.src = BANNER_SCRIPT_URL;
      script.dataset.placement = placementId;
      script.dataset.size = `${width}x${height}`;
      script.dataset.frameOrigin = BANNER_FRAME_ORIGIN;
      script.addEventListener(
        "error",
        () => console.error("Offerwall.me banner script failed to load."),
        { once: true },
      );
      container.appendChild(script);
    };

    loadBanner();
    desktop.addEventListener("change", loadBanner);

    return () => {
      desktop.removeEventListener("change", loadBanner);
      script?.remove();
      container.replaceChildren();
    };
  }, [enabled, placementId]);

  if (!enabled || !placementId) return null;

  return (
    <section
      aria-label="Offerwall.me sponsored advertisement"
      className="ad-provider-offerwall-me-banner"
      style={{
        alignItems: "center",
        display: "flex",
        flexDirection: "column",
        maxWidth: "100%",
        overflow: "hidden",
      }}
    >
      <p className="muted" style={{ margin: "0 0 8px" }}>Sponsored</p>
      <div
        ref={containerRef}
        style={{ height: 250, maxWidth: "100%", width: 300 }}
      />
    </section>
  );
}
