"use client";

import { useState } from "react";
import { AmanahAd } from "./amanah-ad";
import { amanahAdDimensions, type AdSize, type AdType } from "./types";
import { useAmanahPopup } from "./use-amanah-popup";
import { Button } from "../../../ui/button";

const formats = [
  { id: "REWARDED", label: "Rewarded", size: "HALF_PAGE" },
  { id: "INTERSTITIAL", label: "Interstitial", size: "HALF_PAGE" },
  { id: "BANNER", label: "Banner", size: "LEADERBOARD" },
  { id: "VIDEO", label: "Video", size: "LEADERBOARD" },
] as const;

export function AmanahAdsPlacement() {
  const [format, setFormat] = useState<(typeof formats)[number]["id"]>("REWARDED");
  const instanceKey = process.env.NEXT_PUBLIC_AMANAHADS_INSTANCE_KEY?.trim();
  const placement = formats.find((item) => item.id === format) ?? formats[0];
  const size: AdSize = placement.size;
  const type: AdType = placement.id;
  const { width, height } = amanahAdDimensions[size];
  const popup = useAmanahPopup({ adKey: instanceKey ?? "", size, type });

  if (!instanceKey) return null;

  return (
    <section className="amanah-ads" aria-labelledby="amanah-ads-title">
      <div className="amanah-ads-heading">
        <div>
          <p className="eyebrow">SPONSORED ADS</p>
          <h2 id="amanah-ads-title">Watch and discover</h2>
          <p className="muted">Choose an ad format to view available AmanahAds placements.</p>
        </div>
        <div className="amanah-ad-formats" aria-label="AmanahAds format">
          {formats.map((item) => (
            <button
              aria-pressed={format === item.id}
              className={format === item.id ? "amanah-ad-format active" : "amanah-ad-format"}
              key={item.id}
              onClick={() => setFormat(item.id)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>
      <div className="amanah-ad-frame" style={{ aspectRatio: `${width} / ${height}`, width: `min(100%, ${width}px)` }}>
        <AmanahAd adKey={instanceKey} size={size} type={type} />
      </div>
      <div className="amanah-ad-actions">
        <Button onClick={popup.openPopup} type="button" variant="outline">Open ad in popup</Button>
      </div>
      {popup.isOpen && (
        <div className="amanah-popup-overlay" onClick={popup.closePopup} role="presentation">
          <section
            aria-label="AmanahAds popup advertisement"
            aria-modal="true"
            className="amanah-popup"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
          >
            <button
              aria-label="Close advertisement"
              className="amanah-popup-close"
              onClick={popup.closePopup}
              type="button"
            >
              ×
            </button>
            <iframe
              allow="autoplay; fullscreen"
              allowFullScreen
              height={height}
              ref={popup.iframeRef}
              referrerPolicy="strict-origin-when-cross-origin"
              scrolling="no"
              src={popup.frameUrl}
              title={`AmanahAds ${placement.label} popup advertisement`}
              width={width}
            />
          </section>
        </div>
      )}
      <p className="amanah-ads-disclaimer">
        Ad views are provided by AmanahAds. This iframe does not verify completed offers or credit WorkBit wallet rewards.
      </p>
    </section>
  );
}
