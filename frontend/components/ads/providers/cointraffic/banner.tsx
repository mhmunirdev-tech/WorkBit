"use client";

import { ScriptPlacement } from "../shared/script-placement";

export function CointrafficPlacement() {
  const enabled = process.env.NEXT_PUBLIC_COINTRAFFIC_ENABLED?.toLowerCase() === "true";
  const scriptSrc = process.env.NEXT_PUBLIC_COINTRAFFIC_TAG_SRC?.trim();
  const zoneId = process.env.NEXT_PUBLIC_COINTRAFFIC_ZONE_ID?.trim();

  if (!enabled || !scriptSrc) return null;

  return <ScriptPlacement provider="cointraffic" scriptSrc={scriptSrc} zoneId={zoneId} width={728} height={90} />;
}
