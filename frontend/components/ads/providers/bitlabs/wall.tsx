"use client";

import { useEffect, useState } from "react";
import { ApiError, api } from "../../../../lib/api";
import { Alert, AlertDescription } from "../../../ui/alert";
import { Button } from "../../../ui/button";
import { Skeleton } from "../../../ui/skeleton";

type BitLabsWallResponse = {
  wall_url: string;
};

export function BitLabsOfferWall() {
  const [wallUrl, setWallUrl] = useState("");
  const [error, setError] = useState("");
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    let active = true;
    api<BitLabsWallResponse>("/offers/providers/bitlabs/wall-url")
      .then((result) => {
        if (active) setWallUrl(result.wall_url);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        if (reason instanceof ApiError && reason.status === 404) {
          setHidden(true);
          return;
        }
        setError(
          reason instanceof ApiError && reason.status === 402
            ? "An approved earning package is required to view BitLabs offers."
            : reason instanceof Error
              ? reason.message
              : "BitLabs offers could not be loaded.",
        );
      });

    return () => {
      active = false;
    };
  }, []);

  if (hidden) return null;

  return (
    <section className="bitlabs-wall" aria-labelledby="bitlabs-wall-title">
      <div className="bitlabs-wall-heading">
        <div>
          <p className="eyebrow">BITLABS PARTNER OFFERS</p>
          <h2 id="bitlabs-wall-title">Surveys, games &amp; offers</h2>
          <p className="muted">
            Complete eligible BitLabs activities. WorkBit credits rewards only after provider confirmation.
          </p>
        </div>
      </div>
      {error ? (
        <Alert className="state error-state" variant="destructive">
          <AlertDescription>
            <span>{error}</span>
            {error.includes("earning package") && (
              <Button asChild className="bitlabs-wall-action" type="button" variant="outline">
                <a href="/packages">View earning packages</a>
              </Button>
            )}
          </AlertDescription>
        </Alert>
      ) : wallUrl ? (
        <iframe
          className="bitlabs-wall-frame"
          loading="lazy"
          referrerPolicy="strict-origin-when-cross-origin"
          src={wallUrl}
          title="BitLabs surveys, games and offers"
        />
      ) : (
        <div className="bitlabs-wall-loading" aria-label="Loading BitLabs offers">
          <Skeleton className="h-8 w-1/3" />
          <Skeleton className="h-64 w-full" />
        </div>
      )}
      <p className="bitlabs-wall-note">
        Offer eligibility, completion status, and final rewards are determined by BitLabs. Please review each offer&apos;s requirements.
      </p>
    </section>
  );
}
