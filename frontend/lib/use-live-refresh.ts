"use client";

import { useEffect, useRef } from "react";

type LiveRefreshOptions = {
  intervalMs?: number;
  eventName?: string;
};

export function useLiveRefresh(
  refresh: () => void | Promise<void>,
  { intervalMs = 10_000, eventName }: LiveRefreshOptions = {},
) {
  const refreshRef = useRef(refresh);

  useEffect(() => {
    refreshRef.current = refresh;
  }, [refresh]);

  useEffect(() => {
    const refreshIfVisible = () => {
      if (document.visibilityState === "visible") void refreshRef.current();
    };
    const timer = window.setInterval(refreshIfVisible, intervalMs);
    window.addEventListener("focus", refreshIfVisible);
    document.addEventListener("visibilitychange", refreshIfVisible);
    if (eventName) window.addEventListener(eventName, refreshIfVisible);

    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", refreshIfVisible);
      document.removeEventListener("visibilitychange", refreshIfVisible);
      if (eventName) window.removeEventListener(eventName, refreshIfVisible);
    };
  }, [eventName, intervalMs]);
}
