"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { AdSize, AdType } from "./types";

const APP_URL = "https://amanahads.com";

interface AmanahPopupOptions {
  adKey: string;
  type: AdType;
  size: AdSize;
}

export function useAmanahPopup({ adKey, type, size }: AmanahPopupOptions) {
  const [isOpen, setIsOpen] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const frameUrl = new URL("/api/ads/frame", APP_URL);
  frameUrl.searchParams.set("key", adKey);
  frameUrl.searchParams.set("type", type);
  frameUrl.searchParams.set("size", size);

  const openPopup = useCallback(() => setIsOpen(true), []);
  const closePopup = useCallback(() => setIsOpen(false), []);

  useEffect(() => {
    if (!isOpen) return;

    function handleMessage(event: MessageEvent<unknown>) {
      if (
        event.origin === APP_URL &&
        event.source === iframeRef.current?.contentWindow &&
        event.data !== null &&
        typeof event.data === "object" &&
        "type" in event.data &&
        event.data.type === "amanah:popup-close"
      ) {
        setIsOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setIsOpen(false);
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("message", handleMessage);
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("message", handleMessage);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  return { closePopup, frameUrl: frameUrl.toString(), iframeRef, isOpen, openPopup };
}
