"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowUpRight, Gamepad2, Search, Smartphone, Sparkles } from "lucide-react";
import { ApiError, api } from "../../../../lib/api";
import { formatUsd } from "../../../../lib/utils";
import { Alert, AlertDescription } from "../../../ui/alert";
import { Badge } from "../../../ui/badge";
import { Button } from "../../../ui/button";
import { Card, CardContent, CardTitle } from "../../../ui/card";
import { Input } from "../../../ui/input";
import { Skeleton } from "../../../ui/skeleton";

type OfferwallGGOffer = {
  id: number;
  provider: string;
  title: string;
  description: string;
  requirements: string;
  image_url: string | null;
  categories: string[];
  devices: string[];
  user_reward_usd: string;
  reward_is_variable: boolean;
  reward_up_to: boolean;
  payment_model: string;
  featured: boolean;
  click_url: string;
};

type OfferwallGGCatalogResponse = {
  offers: OfferwallGGOffer[];
  page: number;
  pages: number;
  total: number;
};

const pageSize = 50;

function offerIcon(offer: OfferwallGGOffer) {
  const categories = offer.categories.join(" ").toLowerCase();
  if (categories.includes("game")) return <Gamepad2 aria-hidden="true" />;
  if (categories.includes("app") || categories.includes("mobile")) {
    return <Smartphone aria-hidden="true" />;
  }
  return <Sparkles aria-hidden="true" />;
}

export function OfferwallGGCatalog() {
  const [offers, setOffers] = useState<OfferwallGGOffer[]>([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");

  const loadPage = useCallback(async (nextPage = 1, append = false) => {
    if (append) setLoadingMore(true);
    else setLoading(true);
    setError("");

    try {
      const result = await api<OfferwallGGCatalogResponse>(
        `/offers/providers/offerwall-gg/catalog?page=${nextPage}&limit=${pageSize}`,
      );
      setOffers((current) => append ? [...current, ...result.offers] : result.offers);
      setPage(result.page);
      setPages(result.pages);
      setTotal(result.total);
    } catch (reason: unknown) {
      setError(
        reason instanceof ApiError && reason.status === 402
          ? "An approved earning package is required to view provider offers."
          : reason instanceof Error
            ? reason.message
            : "Offerwall.GG offers could not be loaded.",
      );
      if (!append) setOffers([]);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, []);

  useEffect(() => {
    void loadPage();
  }, [loadPage]);

  const categories = useMemo(
    () => [...new Set(offers.flatMap((offer) => offer.categories))].sort((a, b) => a.localeCompare(b)),
    [offers],
  );
  const visibleOffers = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return offers.filter((offer) => {
      const matchesCategory =
        category === "all" ||
        offer.categories.some((item) => item.toLocaleLowerCase() === category);
      const matchesSearch =
        !query ||
        `${offer.title} ${offer.description} ${offer.requirements} ${offer.provider} ${offer.categories.join(" ")}`
          .toLocaleLowerCase()
          .includes(query);
      return matchesCategory && matchesSearch;
    });
  }, [category, offers, search]);

  return (
    <section className="offerwall-gg" aria-labelledby="offerwall-gg-title">
      <div className="offerwall-gg-heading">
        <div>
          <p className="eyebrow">PARTNER OFFERS</p>
          <h2 id="offerwall-gg-title">More ways to earn</h2>
          <p className="muted">
            Browse available offers without leaving WorkBit. Eligibility and final rewards depend on each offer&apos;s terms.
          </p>
        </div>
        {!error && (
          <span className="offerwall-gg-count" aria-live="polite">
            {loading ? "Loading offers..." : `${visibleOffers.length} of ${total} offers`}
          </span>
        )}
      </div>

      <div className="offerwall-gg-controls">
        <label className="offerwall-gg-search">
          <span className="sr-only">Search partner offers</span>
          <Search aria-hidden="true" size={17} />
          <Input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search offers"
          />
        </label>
        {categories.length > 0 && (
          <div className="offerwall-gg-categories" aria-label="Filter partner offers by category">
            {["all", ...categories.map((item) => item.toLocaleLowerCase())].map((item) => (
              <button
                aria-pressed={category === item}
                className="offerwall-gg-category"
                key={item}
                onClick={() => setCategory(item)}
                type="button"
              >
                {item === "all" ? "All" : item[0].toUpperCase() + item.slice(1)}
              </button>
            ))}
          </div>
        )}
      </div>

      {error ? (
        <Alert className="offerwall-gg-error" variant="destructive">
          <AlertDescription>
            <span>{error}</span>
            {error === "An approved earning package is required to view provider offers." ? (
              <Button asChild className="offerwall-gg-retry" type="button" variant="outline">
                <a href="/packages">View earning packages</a>
              </Button>
            ) : (
              <Button
                className="offerwall-gg-retry"
                onClick={() => void loadPage()}
                type="button"
                variant="outline"
              >
                Retry
              </Button>
            )}
          </AlertDescription>
        </Alert>
      ) : loading ? (
        <div className="offerwall-gg-grid" aria-label="Loading partner offers">
          {[1, 2, 3, 4].map((item) => (
            <Card className="offerwall-gg-card offerwall-gg-skeleton" key={item}>
              <Skeleton className="offerwall-gg-image-skeleton" />
              <CardContent>
                <Skeleton className="h-4 w-1/3" />
                <Skeleton className="h-5 w-4/5" />
                <Skeleton className="h-4 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : visibleOffers.length > 0 ? (
        <div className="offerwall-gg-grid" aria-label="Offerwall.GG offers">
          {visibleOffers.map((offer) => (
            <Card className="offerwall-gg-card" key={offer.id}>
              <div className="offerwall-gg-art">
                {offer.image_url ? (
                  <img alt="" loading="lazy" referrerPolicy="no-referrer" src={offer.image_url} />
                ) : (
                  <span className="offerwall-gg-art-icon">{offerIcon(offer)}</span>
                )}
                <div className="offerwall-gg-art-badges">
                  <Badge variant="secondary">{offer.provider}</Badge>
                  {offer.featured && <Badge>Featured</Badge>}
                </div>
              </div>
              <CardContent className="offerwall-gg-card-body">
                <CardTitle>{offer.title}</CardTitle>
                <p className="offerwall-gg-description">
                  {offer.description || "Complete the offer requirements to earn a reward."}
                </p>
                {offer.requirements && (
                  <p className="offerwall-gg-requirements">
                    <strong>How to qualify:</strong> {offer.requirements}
                  </p>
                )}
                <div className="offerwall-gg-card-meta">
                  <span>{offer.categories.slice(0, 2).join(" · ") || "Partner offer"}</span>
                  <span>{offer.devices.slice(0, 2).join(" · ") || "Device varies"}</span>
                </div>
                <div className="offerwall-gg-card-footer">
                  <div className="offerwall-gg-reward">
                    <small>{offer.reward_up_to ? "UP TO YOUR REWARD" : "EST. YOUR REWARD"}</small>
                    <strong>{formatUsd(offer.user_reward_usd)}</strong>
                    {offer.reward_is_variable && <small>May vary by completion</small>}
                  </div>
                  <Button asChild className="offerwall-gg-start" size="sm">
                    <a href={offer.click_url} rel="noopener noreferrer" target="_blank">
                      Start offer <ArrowUpRight aria-hidden="true" size={15} />
                    </a>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="offerwall-gg-empty">
          <Sparkles aria-hidden="true" />
          <strong>{offers.length ? "No matching offers" : "No offers available right now"}</strong>
          <span>
            {offers.length
              ? "Try a different search or category."
              : "Check back later; partner inventory changes based on your country and device."}
          </span>
        </div>
      )}
      {!error && !loading && page < pages && (
        <div className="offerwall-gg-more">
          <Button
            disabled={loadingMore}
            onClick={() => void loadPage(page + 1, true)}
            type="button"
            variant="outline"
          >
            {loadingMore ? "Loading..." : "Load more offers"}
          </Button>
        </div>
      )}

      <p className="offerwall-gg-note">
        Rewards shown are estimated from WorkBit&apos;s active reward policy. Provider verification is required before rewards are credited.
      </p>
    </section>
  );
}
