"use client";

import { useEffect, useRef } from "react";

type AdsterraOptions = {
  key: string;
  format: "iframe";
  height: number;
  width: number;
  params: Record<string, never>;
};

declare global {
  interface Window {
    atOptions?: AdsterraOptions;
  }
}

const socialBarScriptUrl = "https://abscloud.org/1/3a95ad97173dbb19b5b3b5aa025259ed";
const nativeBanner = {
  key: "559a9d162a5186421718d40da8d79194",
  containerId: "container-559a9d162a5186421718d40da8d79194",
};
const responsiveUnits = {
  desktop: {
    key: "c1c0d6bad302a9ce66d52278310e11ce",
    width: 728,
    height: 90,
  },
  tablet: {
    key: "1508473778f77617d8dde9ac0a8691b8",
    width: 468,
    height: 60,
  },
  mobile: {
    key: "bdd629e84ff5a6c71f7f987ae9396447",
    width: 320,
    height: 50,
  },
  inContent: {
    key: "90075329f13f5b1e07ae3d20f946b9d4",
    width: 300,
    height: 250,
  },
  portrait: {
    key: "884344f371b15a7ff5429e077558d6ac",
    width: 160,
    height: 300,
  },
  skyscraper: {
    key: "ff5f49e724b8da48a0c2c30f1e197b7d",
    width: 160,
    height: 600,
  },
} as const;

export function AdsterraBannerPlacement() {
  const responsiveBannerRef = useRef<HTMLDivElement>(null);
  const inContentBannerRef = useRef<HTMLDivElement>(null);
  const nativeBannerRef = useRef<HTMLDivElement>(null);
  const portraitBannerRef = useRef<HTMLDivElement>(null);
  const skyscraperBannerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let disposed = false;
    let loadId = 0;
    const adScripts: HTMLScriptElement[] = [];

    const socialScript = document.createElement("script");
    socialScript.async = true;
    socialScript.dataset.cfasync = "false";
    socialScript.dataset.adsterraSocialBar = "true";
    socialScript.src = socialBarScriptUrl;
    socialScript.onerror = () => console.error("Adsterra Social Bar script failed to load.");
    document.body.appendChild(socialScript);

    function clearAdSlots() {
      for (const script of adScripts) script.remove();
      adScripts.length = 0;
      nativeBannerRef.current?.replaceChildren();
      responsiveBannerRef.current?.replaceChildren();
      inContentBannerRef.current?.replaceChildren();
      portraitBannerRef.current?.replaceChildren();
      skyscraperBannerRef.current?.replaceChildren();
    }

    function loadBanner(
      container: HTMLDivElement,
      unit: (typeof responsiveUnits)[keyof typeof responsiveUnits],
      currentLoadId: number,
    ) {
      if (disposed || currentLoadId !== loadId) return Promise.resolve();

      window.atOptions = {
        key: unit.key,
        format: "iframe",
        height: unit.height,
        width: unit.width,
        params: {},
      };

      const script = document.createElement("script");
      script.async = false;
      script.dataset.cfasync = "false";
      script.src = `https://bauval.org/22/${unit.key}`;
      adScripts.push(script);

      return new Promise<void>((resolve) => {
        script.onload = () => resolve();
        script.onerror = () => {
          console.error(`Adsterra ${unit.width}x${unit.height} banner failed to load.`);
          resolve();
        };
        container.appendChild(script);
      });
    }

    function loadNativeBanner(container: HTMLDivElement, currentLoadId: number) {
      if (disposed || currentLoadId !== loadId) return;
      const script = document.createElement("script");
      script.async = true;
      script.dataset.cfasync = "false";
      script.src = `https://bauval.org/21/${nativeBanner.key}`;
      adScripts.push(script);
      script.onerror = () => console.error("Adsterra native banner failed to load.");
      container.appendChild(script);
    }

    async function loadAdSlots() {
      const nativeContainer = nativeBannerRef.current;
      const responsiveContainer = responsiveBannerRef.current;
      const inContentContainer = inContentBannerRef.current;
      const portraitContainer = portraitBannerRef.current;
      const skyscraperContainer = skyscraperBannerRef.current;
      if (
        !nativeContainer ||
        !responsiveContainer ||
        !inContentContainer ||
        !portraitContainer ||
        !skyscraperContainer
      ) return;

      const currentLoadId = ++loadId;
      clearAdSlots();
      const isDesktop = window.matchMedia("(min-width: 1024px)").matches;
      const responsiveUnit = window.matchMedia("(min-width: 768px)").matches
        ? responsiveUnits.desktop
        : window.matchMedia("(min-width: 480px)").matches
          ? responsiveUnits.tablet
          : responsiveUnits.mobile;

      loadNativeBanner(nativeContainer, currentLoadId);
      await loadBanner(responsiveContainer, responsiveUnit, currentLoadId);
      await loadBanner(inContentContainer, responsiveUnits.inContent, currentLoadId);
      if (isDesktop) {
        await loadBanner(portraitContainer, responsiveUnits.portrait, currentLoadId);
        await loadBanner(skyscraperContainer, responsiveUnits.skyscraper, currentLoadId);
      }
    }

    let activeViewport = "";
    const handleViewportChange = () => {
      const nextViewport = window.matchMedia("(min-width: 1024px)").matches
        ? "desktop"
        : window.matchMedia("(min-width: 768px)").matches
          ? "wide"
          : window.matchMedia("(min-width: 480px)").matches
            ? "tablet"
            : "mobile";
      if (nextViewport === activeViewport) return;
      activeViewport = nextViewport;
      void loadAdSlots();
    };
    handleViewportChange();
    window.addEventListener("resize", handleViewportChange);

    return () => {
      disposed = true;
      window.removeEventListener("resize", handleViewportChange);
      clearAdSlots();
      socialScript.remove();
    };
  }, []);

  return (
    <>
      <section aria-label="Sponsored advertisement" className="adsterra-banner adsterra-native">
        <p>Sponsored</p>
        <div id={nativeBanner.containerId} ref={nativeBannerRef} />
      </section>
      <section aria-label="Sponsored advertisement" className="adsterra-banner adsterra-responsive">
        <p>Sponsored</p>
        <div ref={responsiveBannerRef} />
      </section>
      <section aria-label="Sponsored advertisement" className="adsterra-banner adsterra-banner-in-content">
        <p>Sponsored</p>
        <div ref={inContentBannerRef} />
      </section>
      <div className="adsterra-side-units">
        <section aria-label="Sponsored advertisement" className="adsterra-banner adsterra-side">
          <p>Sponsored</p>
          <div ref={portraitBannerRef} />
        </section>
        <section aria-label="Sponsored advertisement" className="adsterra-banner adsterra-side">
          <p>Sponsored</p>
          <div ref={skyscraperBannerRef} />
        </section>
      </div>
    </>
  );
}
