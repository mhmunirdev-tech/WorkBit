"use client";

import { useEffect, useState } from "react";
import { ApiError, api } from "../../../../lib/api";

export function MoonetixOfferWall() {
  const [wallUrl, setWallUrl] = useState("");
  const [hidden, setHidden] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api<{ wall_url: string }>("/offers/providers/moonetix/wall-url")
      .then((result) => {
        if (active) setWallUrl(result.wall_url);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        if (reason instanceof ApiError && reason.status === 404) {
          setHidden(true);
          return;
        }
        setError(reason instanceof Error ? reason.message : "Moonetix offers could not be loaded.");
      });
    return () => {
      active = false;
    };
  }, []);

  if (hidden) return null;

  return (
    <section className="theoremreach-wall" aria-labelledby="moonetix-wall-title">
      <div className="theoremreach-wall-heading">
        <div>
          <p className="eyebrow">MOONETIX OFFERS</p>
          <h2 id="moonetix-wall-title">Complete offers and earn WBC</h2>
        </div>
      </div>
      {error ? (
        <p className="theoremreach-wall-note" role="alert">{error}</p>
      ) : wallUrl ? (
        <iframe
          className="theoremreach-wall-frame"
          loading="lazy"
          referrerPolicy="strict-origin-when-cross-origin"
          src={wallUrl}
          title="Moonetix offers"
        />
      ) : (
        <p className="theoremreach-wall-note">Loading Moonetix offerwall...</p>
      )}
      <p className="theoremreach-wall-note">
        Only verified Moonetix postbacks credit completed offers to your WorkBit wallet.
      </p>
    </section>
  );
}
