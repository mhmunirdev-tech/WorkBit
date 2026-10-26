"use client";

import { useEffect, useRef } from "react";
import type { AdSize, AdType } from "./types";

type RenderMode = "iframe" | "div";

export { amanahAdDimensions } from "./types";
import { amanahAdDimensions } from "./types";

interface AmanahAdProps {
  adKey: string;
  type: AdType;
  size: AdSize;
  mode?: RenderMode;
}

const APP_URL = "https://amanahads.com";

export function AmanahAd({ adKey, type, size, mode = "iframe" }: AmanahAdProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const dimensions = amanahAdDimensions[size];

  useEffect(() => {
    if (mode !== "div") return;

    const existingScript = Array.from(document.scripts).find(
      (script) => script.dataset.amanahKey === adKey,
    );
    if (existingScript) return;

    const script = document.createElement("script");
    script.src = `${APP_URL}/api/ads/serve.js`;
    script.dataset.key = adKey;
    script.dataset.amanahKey = adKey;
    script.async = true;
    document.head.appendChild(script);
  }, [adKey, mode]);

  if (mode === "iframe") {
    const frameUrl = new URL("/api/ads/frame", APP_URL);
    frameUrl.searchParams.set("key", adKey);
    frameUrl.searchParams.set("type", type);
    frameUrl.searchParams.set("size", size);

    return (
      <iframe
        allow="autoplay; fullscreen"
        allowFullScreen
        height={dimensions.height}
        loading="lazy"
        referrerPolicy="strict-origin-when-cross-origin"
        scrolling="no"
        src={frameUrl.toString()}
        style={{ border: "none", display: "block", height: "100%", width: "100%" }}
        title={`AmanahAds ${type.toLowerCase()} advertisement`}
        width={dimensions.width}
      />
    );
  }

  return (
    <div
      ref={containerRef}
      data-size={size}
      data-type={type}
      id={`amanah-ad-${type.toLowerCase()}-${size.toLowerCase()}`}
      style={{ width: dimensions.width, height: dimensions.height }}
    />
  );
}
