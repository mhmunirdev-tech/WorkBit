"use client";

import { useEffect, useRef } from "react";

type ScriptPlacementProps = {
  provider: string;
  scriptSrc: string;
  zoneId?: string;
  width?: number;
  height?: number;
};

/**
 * Loads a provider-generated display tag only when the provider is configured.
 * The provider's dashboard must supply the script URL; no reward is issued by
 * this component and the script is never loaded from a server-side secret.
 */
export function ScriptPlacement({
  provider,
  scriptSrc,
  zoneId,
  width = 300,
  height = 250,
}: ScriptPlacementProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !scriptSrc) return;

    const script = document.createElement("script");
    script.async = true;
    script.src = scriptSrc;
    script.dataset.workbitProvider = provider;
    if (zoneId) script.dataset.zoneId = zoneId;
    document.head.appendChild(script);

    return () => {
      script.remove();
      container.replaceChildren();
    };
  }, [provider, scriptSrc, zoneId]);

  return (
    <section aria-label={`${provider} sponsored advertisement`} className={`ad-provider ad-provider-${provider}`}>
      <p>Sponsored</p>
      <div
        ref={containerRef}
        data-provider={provider}
        data-zone-id={zoneId || undefined}
        style={{ minHeight: height, maxWidth: width, width: "100%" }}
      />
    </section>
  );
}
