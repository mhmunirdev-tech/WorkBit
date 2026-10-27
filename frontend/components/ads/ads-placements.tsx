import { AmanahAdsPlacement } from "./providers/amanahads/placement";
import { AdsterraBannerPlacement } from "./providers/adsterra/banner";

const adProviders = [
  { id: "adsterra", Placement: AdsterraBannerPlacement },
  { id: "amanahads", Placement: AmanahAdsPlacement },
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
