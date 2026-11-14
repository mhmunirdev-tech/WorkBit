"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";

const imaSdkUrl = "https://imasdk.googleapis.com/js/sdkloader/ima3.js";
const vastTagUrl =
  "https://vapid-size.com/dumvF.zLdfGbN-v/Z/GJUb/zeLma9ZuRZgU/1PkwPWT/cq2aMLTJkxZQM/jbE/tRNtzrYlxNOUT/MdyyNcQn";

type ImaAdError = {
  getMessage(): string;
};

type ImaSdkEvent = {
  getAdsManager?: (videoElement: HTMLVideoElement) => ImaAdsManager;
  getError?: () => ImaAdError;
};

type ImaAdsManager = {
  addEventListener(
    eventType: string,
    listener: (event: ImaSdkEvent) => void,
    useCapture?: boolean,
  ): void;
  init(width: number, height: number, viewMode: string): void;
  start(): void;
  destroy(): void;
};

type ImaAdsRequest = {
  adTagUrl: string;
  linearAdSlotWidth: number;
  linearAdSlotHeight: number;
  nonLinearAdSlotWidth: number;
  nonLinearAdSlotHeight: number;
  setAdWillAutoPlay(value: boolean): void;
  setAdWillPlayMuted(value: boolean): void;
};

type ImaDisplayContainer = {
  initialize(): void;
};

type ImaAdsLoader = {
  addEventListener(
    eventType: string,
    listener: (event: ImaSdkEvent) => void,
    useCapture?: boolean,
  ): void;
  requestAds(request: ImaAdsRequest): void;
};

type ImaSdk = {
  AdDisplayContainer: new (
    container: HTMLElement,
    videoElement: HTMLVideoElement,
  ) => ImaDisplayContainer;
  AdsLoader: new (displayContainer: ImaDisplayContainer) => ImaAdsLoader;
  AdsRequest: new () => ImaAdsRequest;
  AdsManagerLoadedEvent: { Type: { ADS_MANAGER_LOADED: string } };
  AdErrorEvent: { Type: { AD_ERROR: string } };
  AdEvent: {
    Type: {
      ALL_ADS_COMPLETED: string;
      CONTENT_PAUSE_REQUESTED: string;
    };
  };
  ViewMode: { NORMAL: string };
};

declare global {
  interface Window {
    google?: { ima?: ImaSdk };
  }
}

let imaSdkPromise: Promise<ImaSdk> | null = null;

function loadImaSdk(): Promise<ImaSdk> {
  const sdk = window.google?.ima;
  if (sdk) return Promise.resolve(sdk);
  if (imaSdkPromise) return imaSdkPromise;

  imaSdkPromise = new Promise<ImaSdk>((resolve, reject) => {
    const script = document.createElement("script");
    script.async = true;
    script.src = imaSdkUrl;
    script.dataset.workbitImaSdk = "true";
    script.onload = () => {
      const loadedSdk = window.google?.ima;
      if (!loadedSdk) {
        imaSdkPromise = null;
        reject(new Error("Google IMA SDK loaded without its API."));
        return;
      }
      resolve(loadedSdk);
    };
    script.onerror = () => {
      imaSdkPromise = null;
      script.remove();
      reject(new Error("Google IMA SDK failed to load."));
    };
    document.head.appendChild(script);
  });

  return imaSdkPromise;
}

export function HilltopAdsVastVideoPlacement() {
  const [sdkLoaded, setSdkLoaded] = useState(false);
  const [status, setStatus] = useState<"idle" | "loading-sdk" | "ready" | "loading-ad" | "playing" | "complete" | "error">("idle");
  const [message, setMessage] = useState("Load the player when you are ready to watch.");
  const videoRef = useRef<HTMLVideoElement>(null);
  const adContainerRef = useRef<HTMLDivElement>(null);
  const adsManagerRef = useRef<ImaAdsManager | null>(null);
  const activeRef = useRef(true);
  const requestIdRef = useRef(0);

  useEffect(() => {
    activeRef.current = true;
    return () => {
      activeRef.current = false;
      requestIdRef.current += 1;
      adsManagerRef.current?.destroy();
      adsManagerRef.current = null;
    };
  }, []);

  function startAd() {
    const ima = window.google?.ima;
    if (!ima) {
      setStatus("loading-sdk");
      setMessage("Loading the sponsored video player…");
      void loadImaSdk()
        .then(() => {
          if (!activeRef.current) return;
          setSdkLoaded(true);
          setStatus("ready");
          setMessage("The player is ready. Click Play sponsored video to request an ad.");
        })
        .catch((reason: unknown) => {
          console.error("HilltopAds video player could not load Google IMA SDK.", reason);
          if (!activeRef.current) return;
          setStatus("error");
          setMessage("The video player could not load. Try loading it again.");
        });
      return;
    }

    const videoElement = videoRef.current;
    const adContainer = adContainerRef.current;
    if (!ima || !videoElement || !adContainer) {
      setStatus("error");
      setMessage("The video player is not ready. Refresh the page and try again.");
      return;
    }

    const requestId = ++requestIdRef.current;
    adsManagerRef.current?.destroy();
    adsManagerRef.current = null;
    setStatus("loading-ad");
    setMessage("Requesting a video ad…");

    function showError(errorMessage: string, detail?: unknown) {
      if (detail) console.error("HilltopAds VAST playback failed.", detail);
      adsManagerRef.current?.destroy();
      adsManagerRef.current = null;
      if (!activeRef.current || requestIdRef.current !== requestId) return;
      setStatus("error");
      setMessage(errorMessage);
    }

    try {
      const displayContainer = new ima.AdDisplayContainer(adContainer, videoElement);
      displayContainer.initialize();

      const loader = new ima.AdsLoader(displayContainer);
      loader.addEventListener(ima.AdErrorEvent.Type.AD_ERROR, (event) => {
        if (!activeRef.current || requestIdRef.current !== requestId) return;
        showError(
          event.getError?.().getMessage() || "No video ad could be played. Try again later.",
          event.getError?.(),
        );
      });
      loader.addEventListener(ima.AdsManagerLoadedEvent.Type.ADS_MANAGER_LOADED, (event) => {
        if (!activeRef.current || requestIdRef.current !== requestId) return;
        const manager = event.getAdsManager?.(videoElement);
        if (!manager) {
          showError("The video ad player returned an invalid response.");
          return;
        }

        adsManagerRef.current = manager;
        manager.addEventListener(ima.AdErrorEvent.Type.AD_ERROR, (adEvent) => {
          if (!activeRef.current || requestIdRef.current !== requestId) return;
          showError(
            adEvent.getError?.().getMessage() || "The video ad could not be played.",
            adEvent.getError?.(),
          );
        });
        manager.addEventListener(ima.AdEvent.Type.CONTENT_PAUSE_REQUESTED, () => {
          if (activeRef.current && requestIdRef.current === requestId) setStatus("playing");
        });
        manager.addEventListener(ima.AdEvent.Type.ALL_ADS_COMPLETED, () => {
          if (!activeRef.current || requestIdRef.current !== requestId) return;
          manager.destroy();
          adsManagerRef.current = null;
          setStatus("complete");
          setMessage("Sponsored video finished. No WorkBit reward is earned for watching this ad.");
        });

        try {
          const bounds = adContainer.getBoundingClientRect();
          const width = Math.max(1, Math.round(bounds.width));
          const height = Math.max(1, Math.round(bounds.height));
          manager.init(width, height, ima.ViewMode.NORMAL);
          manager.start();
        } catch (reason: unknown) {
          showError("The video ad could not be started.", reason);
        }
      });

      const request = new ima.AdsRequest();
      request.adTagUrl = vastTagUrl;
      const bounds = adContainer.getBoundingClientRect();
      request.linearAdSlotWidth = Math.max(1, Math.round(bounds.width));
      request.linearAdSlotHeight = Math.max(1, Math.round(bounds.height));
      request.nonLinearAdSlotWidth = Math.max(1, Math.round(bounds.width));
      request.nonLinearAdSlotHeight = Math.max(1, Math.round(bounds.height / 3));
      request.setAdWillAutoPlay(false);
      request.setAdWillPlayMuted(false);
      loader.requestAds(request);
    } catch (reason: unknown) {
      showError("The video ad could not be started.", reason);
    }
  }

  const isBusy = status === "loading-sdk" || status === "loading-ad" || status === "playing";

  return (
    <section className="hilltop-vast-placement" aria-labelledby="hilltop-vast-title">
      <div className="hilltop-vast-heading">
        <div>
          <p className="eyebrow">SPONSORED</p>
          <h2 id="hilltop-vast-title">Watch a video ad</h2>
        </div>
        <p>Watching this video does not add a reward to your WorkBit wallet.</p>
      </div>
      <div className="hilltop-vast-player">
        <video ref={videoRef} playsInline />
        <div ref={adContainerRef} className="hilltop-vast-ad-container" aria-label="Sponsored video ad" />
      </div>
      <div className="hilltop-vast-controls">
        <Button type="button" onClick={startAd} disabled={isBusy || status === "complete"}>
          {status === "loading-sdk"
            ? "Loading player…"
            : status === "loading-ad"
              ? "Loading video…"
              : status === "playing"
                ? "Video playing…"
                : status === "complete"
                  ? "Video completed"
                  : status === "error"
                    ? sdkLoaded
                      ? "Try video again"
                      : "Retry player load"
                    : status === "idle"
                      ? "Load video player"
                    : "Play sponsored video"}
        </Button>
        <p role="status" aria-live="polite">{message}</p>
      </div>
    </section>
  );
}
