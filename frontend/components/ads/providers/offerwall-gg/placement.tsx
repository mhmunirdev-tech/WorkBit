"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ApiError, api } from "../../../../lib/api";
import { Alert, AlertDescription } from "../../../ui/alert";
import { Button } from "../../../ui/button";
import { Skeleton } from "../../../ui/skeleton";

export function OfferwallGGPlacement() {
  const [wallUrl, setWallUrl] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);

  const loadWallUrl = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await api<{ wall_url: string }>("/offers/providers/offerwall-gg/wall-url");
      setWallUrl(result.wall_url);
    } catch (reason: unknown) {
      setWallUrl("");
      if (reason instanceof ApiError && reason.status === 402) {
        setError("An approved earning package is required to use this offerwall.");
      } else {
        setError(reason instanceof Error ? reason.message : "Offerwall.GG could not be loaded.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadWallUrl();
  }, [attempt, loadWallUrl]);

  return (
    <section className="offerwall-gg" aria-labelledby="offerwall-gg-title">
      <div className="offerwall-gg-heading">
        <div>
          <p className="eyebrow">OFFERWALL</p>
          <h2 id="offerwall-gg-title">More ways to earn</h2>
          <p className="muted">Complete eligible offers in the secure Offerwall.GG wall.</p>
        </div>
      </div>
      {loading ? (
        <div className="offerwall-gg-loading" aria-label="Loading Offerwall.GG">
          <Skeleton className="h-5 w-2/3" />
          <Skeleton className="h-5 w-1/2" />
          <Skeleton className="h-5 w-3/4" />
        </div>
      ) : error ? (
        <Alert className="offerwall-gg-error" variant="destructive">
          <AlertDescription>
            {error}
            {error === "An approved earning package is required to use this offerwall." ? (
              <Button asChild className="offerwall-gg-retry" type="button" variant="outline">
                <Link href="/packages">View earning packages</Link>
              </Button>
            ) : (
              <Button
                className="offerwall-gg-retry"
                onClick={() => setAttempt((current) => current + 1)}
                type="button"
                variant="outline"
              >
                Retry
              </Button>
            )}
          </AlertDescription>
        </Alert>
      ) : (
        <iframe
          allow="clipboard-write"
          className="offerwall-gg-frame"
          loading="lazy"
          referrerPolicy="strict-origin-when-cross-origin"
          src={wallUrl}
          title="Offerwall.GG earning offers"
        />
      )}
      <p className="offerwall-gg-note">
        Rewards are credited only after WorkBit verifies Offerwall.GG&apos;s signed server callback. Reversals may reduce the available balance.
      </p>
    </section>
  );
}
