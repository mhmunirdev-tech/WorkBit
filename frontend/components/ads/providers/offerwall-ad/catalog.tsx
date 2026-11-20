import { Sparkles } from "lucide-react";
import { Badge } from "../../../ui/badge";

export function OfferwallAdCatalog() {
  return (
    <section
      className="offerwall-gg offerwall-ad-catalog"
      aria-labelledby="offerwall-ad-title"
    >
      <div className="offerwall-gg-heading">
        <div>
          <p className="eyebrow">OFFERWALL AD</p>
          <h2 id="offerwall-ad-title">Discover more offers</h2>
          <p className="muted">
            Browse partner tasks and earn rewards after verified completion.
          </p>
        </div>
        <Badge variant="secondary">Partner connected</Badge>
      </div>

      <div className="offerwall-gg-empty">
        <Sparkles aria-hidden="true" />
        <strong>Offer cards are being connected</strong>
        <span>
          Offerwall Ad reward callbacks are configured. Its catalog will appear
          here once the provider offer fields are mapped.
        </span>
      </div>
    </section>
  );
}
