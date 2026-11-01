"use client";

import { useEffect, useState } from "react";
import { ApiError, api } from "../../../../lib/api";
import { Alert, AlertDescription } from "../../../ui/alert";
import { Button } from "../../../ui/button";
import { Skeleton } from "../../../ui/skeleton";

type CPXResearchWallResponse = {
  wall_url: string;
};

export function CPXResearchOfferWall() {
  const [wallUrl, setWallUrl] = useState("");
  const [error, setError] = useState("");
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    let active = true;
    api<CPXResearchWallResponse>("/offers/providers/cpx-research/wall-url")
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
            ? "An approved earning package is required to view CPX Research surveys."
            : reason instanceof Error
              ? reason.message
              : "CPX Research surveys could not be loaded.",
        );
      });

    return () => {
      active = false;
    };
  }, []);

  if (hidden) return null;

  return (
    <section className="theoremreach-wall" aria-labelledby="cpx-research-wall-title">
      <div className="theoremreach-wall-heading">
        <div>
          <p className="eyebrow">CPX RESEARCH SURVEYS</p>
          <h2 id="cpx-research-wall-title">Complete surveys</h2>
          <p className="muted">
            Survey availability and completion are determined by CPX Research.
          </p>
        </div>
      </div>
      {error ? (
        <Alert className="state error-state" variant="destructive">
          <AlertDescription>
            <span>{error}</span>
            {error.includes("earning package") && (
              <Button asChild className="theoremreach-wall-action" type="button" variant="outline">
                <a href="/packages">View earning packages</a>
              </Button>
            )}
          </AlertDescription>
        </Alert>
      ) : wallUrl ? (
        <iframe
          className="theoremreach-wall-frame"
          loading="lazy"
          referrerPolicy="strict-origin-when-cross-origin"
          src={wallUrl}
          title="CPX Research surveys"
        />
      ) : (
        <div className="theoremreach-wall-loading" aria-label="Loading CPX Research surveys">
          <Skeleton className="h-8 w-1/3" />
          <Skeleton className="h-64 w-full" />
        </div>
      )}
      <p className="theoremreach-wall-note">
        CPX completion rewards will be credited only after its verified server callback is configured.
      </p>
    </section>
  );
}
