import { AmanahAdsPlacement } from "./providers/amanahads/placement";
import { AdsterraBannerPlacement } from "./providers/adsterra/banner";
import { AAdsBannerPlacement } from "./providers/a-ads/banner";
import { BitmediaPlacement } from "./providers/bitmedia/banner";
import { CointrafficPlacement } from "./providers/cointraffic/banner";
import { CoinzillaNativePlacement } from "./providers/coinzilla/native";
import { MonetagPlacement } from "./providers/monetag/tag";
import { PropellerAdsPlacement } from "./providers/propellerads/tag";

const adProviders = [
  { id: "adsterra", Placement: AdsterraBannerPlacement },
  { id: "amanahads", Placement: AmanahAdsPlacement },
  { id: "a-ads", Placement: AAdsBannerPlacement },
  { id: "coinzilla", Placement: CoinzillaNativePlacement },
  { id: "cointraffic", Placement: CointrafficPlacement },
  { id: "propellerads", Placement: PropellerAdsPlacement },
  { id: "monetag", Placement: MonetagPlacement },
  { id: "bitmedia", Placement: BitmediaPlacement },
] as const;

export function AdsPlacements() {
  return (
    <>
      {adProviders.map(({ id, Placement }) => (
        <Placement key={id} />
      ))}
    </>
  );
}
