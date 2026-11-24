"use client";

import { useEffect, useState } from "react";
import { ApiError, api } from "../../../../lib/api";
import { Alert, AlertDescription } from "../../../ui/alert";
import { Badge } from "../../../ui/badge";
import { Skeleton } from "../../../ui/skeleton";

type OfferwallAdWallResponse = {
  wall_url: string;
};

export function OfferwallAdCatalog() {
  const [wallUrl, setWallUrl] = useState("");
  const [error, setError] = useState("");
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    let active = true;
    api<OfferwallAdWallResponse>("/offers/providers/offerwall-ad/wall-url")
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
          reason instanceof Error
            ? reason.message
            : "Offerwall Ad offers could not be loaded.",
        );
      });

    return () => {
      active = false;
    };
  }, []);

  if (hidden) return null;

  return (
    <article
      className="offerwall-gg offerwall-ad-catalog"
      aria-labelledby="offerwall-ad-title"
    >
      <div className="offerwall-gg-heading">
        <div>
          <p className="eyebrow">OFFERWALL AD</p>
          <h2 id="offerwall-ad-title">Complete offers and earn WBC</h2>
          <p className="muted">
            Browse eligible partner offers. WorkBit credits rewards after verified completion.
          </p>
        </div>
        <Badge variant="secondary">Hosted offerwall</Badge>
      </div>

      {error ? (
        <Alert className="offerwall-gg-error" variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : wallUrl ? (
        <iframe
          className="offerwall-ad-frame"
          loading="lazy"
          referrerPolicy="strict-origin-when-cross-origin"
          src={wallUrl}
          title="Offerwall Ad offers"
        />
      ) : (
        <div className="offerwall-ad-loading" aria-label="Loading Offerwall Ad">
          <Skeleton className="h-8 w-1/3" />
          <Skeleton className="h-64 w-full" />
        </div>
      )}

      <p className="offerwall-ad-note">
        Offerwall Ad determines offer eligibility and confirmation. WorkBit applies its reward policy when a verified callback arrives.
      </p>
    </article>
  );
}
