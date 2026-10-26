import { AmanahAdsPlacement } from "./providers/amanahads/placement";

const adProviders = [
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
