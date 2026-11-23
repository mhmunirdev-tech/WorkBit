"use client";

import Image from "next/image";
import { useEffect, useMemo, useState } from "react";
import { ArrowUpRight, Search, ShoppingBag } from "lucide-react";
import { ApiError, api } from "../../../../lib/api";
import { Alert, AlertDescription } from "../../../ui/alert";
import { Badge } from "../../../ui/badge";
import { Button } from "../../../ui/button";
import { Card, CardContent, CardTitle } from "../../../ui/card";
import { Input } from "../../../ui/input";
import { Skeleton } from "../../../ui/skeleton";

type AdmitadAction = {
  name: string;
  type: string;
  payment_size: string;
};

type AdmitadCampaign = {
  id: number;
  name: string;
  description: string;
  image_url: string | null;
  currency: string;
  actions: AdmitadAction[];
};

type AdmitadCampaignsResponse = {
  campaigns: AdmitadCampaign[];
  total: number;
};

export function AdmitadCatalog() {
  const [campaigns, setCampaigns] = useState<AdmitadCampaign[]>([]);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [hidden, setHidden] = useState(false);
  const [loading, setLoading] = useState(true);
  const [openingId, setOpeningId] = useState<number | null>(null);

  useEffect(() => {
    let active = true;
    api<AdmitadCampaignsResponse>("/offers/providers/admitad/catalog")
      .then((result) => {
        if (active) setCampaigns(result.campaigns);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        if (reason instanceof ApiError && reason.status === 404) {
          setHidden(true);
          return;
        }
        setError(reason instanceof Error ? reason.message : "Partner deals could not be loaded.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const visibleCampaigns = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    if (!query) return campaigns;
    return campaigns.filter((campaign) =>
      `${campaign.name} ${campaign.description} ${campaign.actions
        .map((action) => `${action.name} ${action.type}`)
        .join(" ")}`
        .toLocaleLowerCase()
        .includes(query),
    );
  }, [campaigns, search]);

  async function visitCampaign(campaignId: number) {
    setOpeningId(campaignId);
    setError("");
    try {
      const result = await api<{ link_url: string }>(
        `/offers/providers/admitad/campaigns/${campaignId}/link`,
      );
      const link = new URL(result.link_url);
      if (link.protocol !== "https:" || link.hostname !== "ad.admitad.com" || !link.pathname.startsWith("/goto/")) {
        throw new Error("Admitad returned an invalid partner link.");
      }
      window.location.assign(link.toString());
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "The partner link could not be created.");
      setOpeningId(null);
    }
  }

  if (hidden) return null;

  return (
    <section className="offerwall-gg admitad-catalog" aria-labelledby="admitad-catalog-title">
      <div className="offerwall-gg-heading">
        <div>
          <p className="eyebrow">ADMITAD PARTNER DEALS</p>
          <h2 id="admitad-catalog-title">Shop with partner stores</h2>
          <p className="muted">
            Visit participating stores through tracked links. These purchases do not earn WorkBit rewards or cashback.
          </p>
        </div>
        {!error && (
          <span className="offerwall-gg-count" aria-live="polite">
            {loading ? "Loading partner deals..." : `${visibleCampaigns.length} of ${campaigns.length} stores`}
          </span>
        )}
      </div>

      {campaigns.length > 0 && (
        <label className="offerwall-gg-search admitad-search">
          <span className="sr-only">Search partner stores</span>
          <Search aria-hidden="true" size={17} />
          <Input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search partner stores"
          />
        </label>
      )}

      {error ? (
        <Alert className="offerwall-gg-error" variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : loading ? (
        <div className="offerwall-gg-grid" aria-label="Loading partner stores">
          {[1, 2, 3].map((item) => (
            <Card className="offerwall-gg-card offerwall-gg-skeleton" key={item}>
              <CardContent>
                <Skeleton className="h-5 w-3/5" />
                <Skeleton className="mt-3 h-4 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : visibleCampaigns.length > 0 ? (
        <div className="offerwall-gg-grid" aria-label="Admitad partner stores">
          {visibleCampaigns.map((campaign) => (
            <Card className="offerwall-gg-card" key={campaign.id}>
              <div className="offerwall-gg-art admitad-art">
                {campaign.image_url ? (
                  <Image alt="" height={132} src={campaign.image_url} unoptimized width={300} />
                ) : (
                  <span className="offerwall-gg-art-icon"><ShoppingBag aria-hidden="true" /></span>
                )}
                <div className="offerwall-gg-art-badges">
                  <Badge variant="secondary">Admitad</Badge>
                  {campaign.currency && <Badge>{campaign.currency}</Badge>}
                </div>
              </div>
              <CardContent className="offerwall-gg-card-body">
                <CardTitle>{campaign.name}</CardTitle>
                <p className="offerwall-gg-description">
                  {campaign.description || "Visit this partner store and review its current terms."}
                </p>
                {campaign.actions.length > 0 && (
                  <ul className="admitad-action-list" aria-label="Partner commission terms">
                    {campaign.actions.slice(0, 3).map((action, index) => (
                      <li key={`${campaign.id}-${action.name}-${index}`}>
                        <span>{action.name || action.type || "Eligible action"}</span>
                        {action.payment_size && <strong>{action.payment_size}</strong>}
                      </li>
                    ))}
                  </ul>
                )}
                <div className="offerwall-gg-card-footer">
                  <span className="admitad-commission-note">Commission is subject to Admitad and store terms.</span>
                  <Button
                    className="offerwall-gg-start"
                    disabled={openingId !== null}
                    onClick={() => void visitCampaign(campaign.id)}
                    size="sm"
                    type="button"
                  >
                    {openingId === campaign.id ? "Opening..." : "Visit store"}
                    {openingId !== campaign.id && <ArrowUpRight aria-hidden="true" size={15} />}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="offerwall-gg-empty">
          <ShoppingBag aria-hidden="true" />
          <strong>{campaigns.length ? "No matching stores" : "No approved stores available"}</strong>
          <span>
            {campaigns.length
              ? "Try another search."
              : "Admitad displays stores after your ad space and program applications are approved."}
          </span>
        </div>
      )}

      <p className="offerwall-gg-note">
        WorkBit may earn an affiliate commission from eligible purchases. Prices, promotions, eligibility, and commission are controlled by each store.
      </p>
    </section>
  );
}
