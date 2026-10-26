import { AmanahAdsPlacement } from "./providers/amanahads/placement";
import { OfferwallGGPlacement } from "./providers/offerwall-gg/placement";

const adProviders = [
  { id: "amanahads", Placement: AmanahAdsPlacement },
  { id: "offerwall-gg", Placement: OfferwallGGPlacement },
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
