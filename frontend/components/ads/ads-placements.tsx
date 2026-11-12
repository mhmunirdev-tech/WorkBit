import { AmanahAdsPlacement } from "./providers/amanahads/placement";
import { AdsterraBannerPlacement } from "./providers/adsterra/banner";
import { AAdsBannerPlacement } from "./providers/a-ads/banner";
import { BitmediaPlacement } from "./providers/bitmedia/banner";
import { CointrafficPlacement } from "./providers/cointraffic/banner";
import { CoinzillaNativePlacement } from "./providers/coinzilla/native";
import { MonetagPlacement } from "./providers/monetag/tag";
import { PropellerAdsPlacement } from "./providers/propellerads/tag";
import { HilltopAdsVastVideoPlacement } from "./providers/hilltopads/vast-video";

const adProviders = [
  { id: "adsterra", name: "Adsterra", configured: true, Placement: AdsterraBannerPlacement },
  {
    id: "amanahads",
    name: "AmanahAds",
    configured: Boolean(process.env.NEXT_PUBLIC_AMANAHADS_INSTANCE_KEY?.trim()),
    Placement: AmanahAdsPlacement,
  },
  {
    id: "a-ads",
    name: "A-ADS",
    configured:
      process.env.NEXT_PUBLIC_AADS_ENABLED?.toLowerCase() === "true" &&
      Boolean(process.env.NEXT_PUBLIC_AADS_UNIT_ID?.trim()),
    Placement: AAdsBannerPlacement,
  },
  {
    id: "coinzilla",
    name: "Coinzilla",
    configured:
      process.env.NEXT_PUBLIC_COINZILLA_ENABLED?.toLowerCase() === "true" &&
      Boolean(process.env.NEXT_PUBLIC_COINZILLA_ZONE_ID?.trim()),
    Placement: CoinzillaNativePlacement,
  },
  {
    id: "cointraffic",
    name: "Cointraffic",
    configured:
      process.env.NEXT_PUBLIC_COINTRAFFIC_ENABLED?.toLowerCase() === "true" &&
      Boolean(process.env.NEXT_PUBLIC_COINTRAFFIC_TAG_SRC?.trim()),
    Placement: CointrafficPlacement,
  },
  {
    id: "propellerads",
    name: "PropellerAds",
    configured:
      process.env.NEXT_PUBLIC_PROPELLERADS_ENABLED?.toLowerCase() === "true" &&
      Boolean(process.env.NEXT_PUBLIC_PROPELLERADS_TAG_SRC?.trim()),
    Placement: PropellerAdsPlacement,
  },
  {
    id: "monetag",
    name: "Monetag",
    configured:
      process.env.NEXT_PUBLIC_MONETAG_ENABLED?.toLowerCase() === "true" &&
      Boolean(process.env.NEXT_PUBLIC_MONETAG_TAG_SRC?.trim()),
    Placement: MonetagPlacement,
  },
  {
    id: "bitmedia",
    name: "Bitmedia",
    configured:
      process.env.NEXT_PUBLIC_BITMEDIA_ENABLED?.toLowerCase() === "true" &&
      Boolean(process.env.NEXT_PUBLIC_BITMEDIA_PLACEMENT_ID?.trim()),
    Placement: BitmediaPlacement,
  },
  {
    id: "hilltopads-vast-video",
    name: "HilltopAds",
    configured: true,
    Placement: HilltopAdsVastVideoPlacement,
  },
] as const;

export function AdsPlacements() {
  return (
    <div className="ads-agency-list" aria-label="Advertising partners">
      {adProviders.map(({ id, name, configured, Placement }) => {
        const isActive = configured;
        const status = configured ? "Integration enabled" : "Setup required";

        return (
          <section className="ads-agency-card" key={id} aria-labelledby={`${id}-agency-title`}>
            <header className="ads-agency-card-heading">
              <h2 id={`${id}-agency-title`}>{name}</h2>
              <span className={isActive ? "ads-agency-status is-enabled" : "ads-agency-status"}>
                {status}
              </span>
            </header>
            {isActive ? (
              <Placement />
            ) : (
              <p className="ads-agency-card-note">
                {`Add the approved ${name} placement settings to the frontend environment to show its ads.`}
              </p>
            )}
          </section>
        );
      })}
    </div>
  );
}
