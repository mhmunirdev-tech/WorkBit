"use client";

import { useEffect, useRef, useState } from "react";
import { ApiError, api } from "../../../../lib/api";
import { Alert, AlertDescription } from "../../../ui/alert";
import { Skeleton } from "../../../ui/skeleton";

type BitcoTasksSdkConfig = {
  api_key: string;
  sub_id: string;
  sig?: string;
};

type BitcoTasksWall = {
  destroy: () => void;
};

type BitcoTasksSdk = {
  mount: (
    target: HTMLElement,
    options: {
      apiKey: string;
      subId: string;
      sig?: string;
      title: string;
      theme: "light";
      accent: string;
      categories: string[];
      hideEmpty: boolean;
      wallet: true;
    },
  ) => BitcoTasksWall;
};

declare global {
  interface Window {
    BitcoTasks?: BitcoTasksSdk;
  }
}

const SDK_SCRIPTS = [
  "https://bitcotasks.com/sdk/bitcotasks-sdk-v2.js",
  "https://bitcotasks.com/sdk/bitcotasks-sdk-v2-ui.js",
];

let sdkLoadPromise: Promise<void> | null = null;

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      `script[data-bitcotasks-src="${src}"]`,
    );
    if (existing?.dataset.loaded === "true") {
      resolve();
      return;
    }

    const script = existing ?? document.createElement("script");
    const onLoad = () => {
      script.dataset.loaded = "true";
      resolve();
    };
    const onError = () => {
      script.remove();
      reject(new Error("BitcoTasks offerwall script could not be loaded."));
    };

    script.addEventListener("load", onLoad, { once: true });
    script.addEventListener("error", onError, { once: true });
    if (!existing) {
      script.src = src;
      script.async = true;
      script.dataset.bitcotasksSrc = src;
      document.head.appendChild(script);
    }
  });
}

function loadBitcoTasksSdk(): Promise<void> {
  if (!sdkLoadPromise) {
    sdkLoadPromise = SDK_SCRIPTS.reduce(
      (pending, src) => pending.then(() => loadScript(src)),
      Promise.resolve(),
    )
      .then(() => {
        if (!window.BitcoTasks?.mount) {
          throw new Error("BitcoTasks offerwall is unavailable.");
        }
      })
      .catch((error: unknown) => {
        sdkLoadPromise = null;
        throw error;
      });
  }
  return sdkLoadPromise;
}

export function BitcoTasksOfferWall() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    let active = true;
    let wall: BitcoTasksWall | undefined;

    const mountWall = async () => {
      const config = await api<BitcoTasksSdkConfig>(
        "/offers/providers/bitcotasks/sdk-config",
      );
      await loadBitcoTasksSdk();
      if (!active || !containerRef.current || !window.BitcoTasks?.mount) return;

      wall = window.BitcoTasks.mount(containerRef.current, {
        apiKey: config.api_key,
        subId: config.sub_id,
        sig: config.sig,
        title: "Earn with BitcoTasks",
        theme: "light",
        accent: "#2563eb",
        categories: [
          "ptc",
          "video",
          "faucet",
          "shortlinks",
          "tasks",
          "surveys",
          "offers",
          "article",
        ],
        hideEmpty: true,
        wallet: true,
      });
    };

    void mountWall()
      .catch((reason: unknown) => {
        if (!active) return;
        if (reason instanceof ApiError && reason.status === 404) {
          setHidden(true);
          return;
        }
        setError(
          reason instanceof Error
            ? reason.message
            : "BitcoTasks offers could not be loaded.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
      wall?.destroy();
    };
  }, []);

  if (hidden) return null;

  return (
    <section className="theoremreach-wall" aria-labelledby="bitcotasks-wall-title">
      <div className="theoremreach-wall-heading">
        <div>
          <p className="eyebrow">BITCOTASKS</p>
          <h2 id="bitcotasks-wall-title">Earn from offers and tasks</h2>
          <p className="muted">
            Browse available activities. Availability and rewards are determined
            by BitcoTasks.
          </p>
        </div>
      </div>
      {error ? (
        <Alert className="state error-state" variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : (
        <>
          {loading && (
            <div className="theoremreach-wall-loading" aria-label="Loading BitcoTasks">
              <Skeleton className="h-8 w-1/3" />
              <Skeleton className="h-10 w-full" />
            </div>
          )}
          <div
            className="bitcotasks-wall-container"
            ref={containerRef}
            aria-busy={loading}
          />
        </>
      )}
      <p className="theoremreach-wall-note">
        BitcoTasks credits are added to your WorkBit wallet only after its
        verified server callback is received.
      </p>
    </section>
  );
}
