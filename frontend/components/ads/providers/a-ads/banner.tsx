"use client";

const AADS_FRAME_ORIGIN = "https://acceptable.a-ads.com";

function isEnabled() {
  return process.env.NEXT_PUBLIC_AADS_ENABLED?.toLowerCase() === "true";
}

export function AAdsBannerPlacement() {
  const unitId = process.env.NEXT_PUBLIC_AADS_UNIT_ID?.trim();
  const size = process.env.NEXT_PUBLIC_AADS_UNIT_SIZE?.trim() || "Adaptive";

  if (!isEnabled() || !unitId) return null;

  const frameUrl = `${AADS_FRAME_ORIGIN}/${encodeURIComponent(unitId)}/?size=${encodeURIComponent(size)}`;

  return (
    <section aria-label="A-ADS sponsored advertisement" className="ad-provider ad-provider-a-ads">
      <p>Sponsored</p>
      <iframe
        data-aa={unitId}
        height="90"
        loading="lazy"
        referrerPolicy="no-referrer-when-downgrade"
        src={frameUrl}
        style={{ border: 0, display: "block", height: "auto", margin: "0 auto", maxWidth: "100%", overflow: "hidden", padding: 0, width: "70%" }}
        title="A-ADS advertisement"
      />
    </section>
  );
}
