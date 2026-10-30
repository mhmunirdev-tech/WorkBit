"use client";

import { useEffect } from "react";

const enabled = process.env.NEXT_PUBLIC_MONETAG_ENABLED?.toLowerCase() === "true";

export function MonetagMultitag() {
  useEffect(() => {
    if (!enabled) return;

    const scripts = [
      { src: "https://n6wxm.com/vignette.min.js", zone: "12154839" },
      { src: "https://quge5.com/88/tag.min.js", zone: "303649", cfasync: "false" },
      { src: "https://al5sm.com/tag.min.js", zone: "12154837" },
      { src: "https://al5sm.com/tag.min.js", zone: "12154836" },
    ].map(({ src, zone, cfasync }) => {
      const script = document.createElement("script");
      script.async = true;
      script.src = src;
      script.dataset.zone = zone;
      if (cfasync) script.dataset.cfasync = cfasync;
      script.dataset.workbitMonetag = zone;
      script.onerror = () => {
        console.error(`Monetag script failed to load for zone ${zone}.`);
      };
      document.head.appendChild(script);
      return script;
    });

    return () => {
      scripts.forEach((script) => script.remove());
    };
  }, []);

  return null;
}
