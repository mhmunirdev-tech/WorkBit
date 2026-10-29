"use client";

import { ScriptPlacement } from "../shared/script-placement";

export function MonetagPlacement() {
  const enabled = process.env.NEXT_PUBLIC_MONETAG_ENABLED?.toLowerCase() === "true";
  const scriptSrc = process.env.NEXT_PUBLIC_MONETAG_TAG_SRC?.trim();
  const zoneId = process.env.NEXT_PUBLIC_MONETAG_ZONE_ID?.trim();

  if (!enabled || !scriptSrc) return null;

  return <ScriptPlacement provider="monetag" scriptSrc={scriptSrc} zoneId={zoneId} width={728} height={90} />;
}
