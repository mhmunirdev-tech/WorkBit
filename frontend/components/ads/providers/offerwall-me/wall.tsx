"use client";

import { useEffect, useState } from "react";
import { ApiError, api } from "../../../../lib/api";
import { Alert, AlertDescription } from "../../../ui/alert";
import { Skeleton } from "../../../ui/skeleton";

type OfferwallMeResponse = {
  wall_url: string;
};

export function OfferwallMeWall() {
  const [wallUrl, setWallUrl] = useState("");
  const [error, setError] = useState("");
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    let active = true;
    api<OfferwallMeResponse>("/offers/providers/offerwall-me/wall-url")
      .then((response) => {
        if (active) setWallUrl(response.wall_url);
      })
      .catch((reason: unknown) => {
        if (active) {
          if (reason instanceof ApiError && reason.status === 404) {
            setHidden(true);
            return;
          }
          setError(
            reason instanceof Error
              ? reason.message
              : "Offerwall.me offers could not be loaded.",
          );
        }
      });
    return () => {
      active = false;
    };
  }, []);

  if (hidden) return null;

  return (
    <section className="theoremreach-wall" aria-labelledby="offerwall-me-title">
      <div className="theoremreach-wall-heading">
        <div>
          <p className="eyebrow">OFFERWALL.ME</p>
          <h2 id="offerwall-me-title">Tasks, shortlinks &amp; offers</h2>
          <p className="muted">
            Available actions are determined by Offerwall.me.
          </p>
        </div>
      </div>
      {error ? (
        <Alert className="state error-state" variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : wallUrl ? (
        <iframe
          className="theoremreach-wall-frame"
          loading="lazy"
          referrerPolicy="strict-origin-when-cross-origin"
          src={wallUrl}
          title="Offerwall.me offers"
        />
      ) : (
        <div className="theoremreach-wall-loading" aria-label="Loading Offerwall.me">
          <Skeleton className="h-8 w-1/3" />
          <Skeleton className="h-10 w-36" />
        </div>
      )}
      <p className="theoremreach-wall-note">
        Earnings are credited only after Offerwall.me&apos;s verified server callback.
      </p>
    </section>
  );
}
