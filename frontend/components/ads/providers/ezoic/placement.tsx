"use client";

import { useEffect } from "react";

type EzoicStandalone = {
  cmd?: Array<() => void>;
  showAds?: (options: Record<string, never>) => void;
};

declare global {
  interface Window {
    ezstandalone?: EzoicStandalone;
  }
}

export function EzoicPlacement() {
  const enabled = process.env.NEXT_PUBLIC_EZOIC_ENABLED?.toLowerCase() === "true";

  useEffect(() => {
    if (!enabled) return;

    const standalone = window.ezstandalone;
    if (!standalone?.cmd) {
      console.error("EzoicAds command queue is not initialized.");
      return;
    }

    standalone.cmd.push(() => {
      const showAds = window.ezstandalone?.showAds;
      if (!showAds) {
        console.error("EzoicAds showAds function is unavailable.");
        return;
      }

      showAds({});
    });
  }, [enabled]);

  if (!enabled) return null;

  return (
    <section aria-label="Ezoic sponsored advertisement" className="ad-provider ad-provider-ezoic">
      <p>Sponsored</p>
    </section>
  );
}
