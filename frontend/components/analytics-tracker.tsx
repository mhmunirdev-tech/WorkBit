"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { api } from "../lib/api";

const VISITOR_ID_KEY = "workbit_analytics_visitor_id";

function getVisitorId(): string {
  const existing = window.localStorage.getItem(VISITOR_ID_KEY);
  if (existing) return existing;
  const visitorId = window.crypto.randomUUID();
  window.localStorage.setItem(VISITOR_ID_KEY, visitorId);
  return visitorId;
}

export function AnalyticsTracker() {
  const pathname = usePathname();

  useEffect(() => {
    if (pathname === "/admin" || pathname.startsWith("/admin/")) return;

    let visitorId: string;
    try {
      visitorId = getVisitorId();
    } catch (error) {
      console.warn("Anonymous page-view analytics could not be initialized.", error);
      return;
    }

    const sendActivity = (eventType: "PAGE_VIEW" | "VISITOR_PING") => {
      void api("/analytics/page-view", {
        method: "POST",
        body: JSON.stringify({ visitor_id: visitorId, path: pathname, event_type: eventType }),
      }).catch((error: unknown) => {
        console.warn("Anonymous page-view analytics could not be recorded.", error);
      });
    };
    const pingWhenVisible = () => {
      if (document.visibilityState === "visible") sendActivity("VISITOR_PING");
    };

    sendActivity("PAGE_VIEW");
    const timer = window.setInterval(pingWhenVisible, 3 * 60_000);
    document.addEventListener("visibilitychange", pingWhenVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", pingWhenVisible);
    };
  }, [pathname]);

  return null;
}
