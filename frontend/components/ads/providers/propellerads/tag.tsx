"use client";

import { ScriptPlacement } from "../shared/script-placement";

export function PropellerAdsPlacement() {
  const enabled = process.env.NEXT_PUBLIC_PROPELLERADS_ENABLED?.toLowerCase() === "true";
  const scriptSrc = process.env.NEXT_PUBLIC_PROPELLERADS_TAG_SRC?.trim();
  const zoneId = process.env.NEXT_PUBLIC_PROPELLERADS_ZONE_ID?.trim();

  if (!enabled || !scriptSrc) return null;

  return <ScriptPlacement provider="propellerads" scriptSrc={scriptSrc} zoneId={zoneId} width={728} height={90} />;
}
