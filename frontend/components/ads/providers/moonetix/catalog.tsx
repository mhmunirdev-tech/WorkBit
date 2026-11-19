"use client";

import Image from "next/image";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowUpRight, Gamepad2, Search, Smartphone, Sparkles } from "lucide-react";
import { ApiError, api } from "../../../../lib/api";
import { formatUsd, formatWbcFromUsd } from "../../../../lib/utils";
import { Alert, AlertDescription } from "../../../ui/alert";
import { Badge } from "../../../ui/badge";
import { Button } from "../../../ui/button";
import { Card, CardContent, CardTitle } from "../../../ui/card";
import { Input } from "../../../ui/input";
import { Skeleton } from "../../../ui/skeleton";

type MoonetixGoal = {
  name: string;
  reward: string;
  payout_usd: string;
};

type MoonetixOffer = {
  id: string;
  title: string;
  category: string;
  description: string;
  goals: MoonetixGoal[];
  reward: string;
  reward_max: string | null;
  reward_name: string;
  payout_usd: string;
  estimated_user_reward_usd: string;
  estimated_user_reward_max_usd: string | null;
  is_variable: boolean;
  image_url: string | null;
  start_url: string;
};

type MoonetixOffersResponse = {
  offers: MoonetixOffer[];
  total: number;
  currency: string;
  usd_bdt_rate: string | null;
};

const pageSize = 24;

function offerIcon(category: string) {
  const normalized = category.toLowerCase();
  if (normalized === "game") return <Gamepad2 aria-hidden="true" />;
  if (normalized === "app") return <Smartphone aria-hidden="true" />;
  return <Sparkles aria-hidden="true" />;
}

function formatProviderReward(value: string) {
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function MoonetixCatalog() {
  const [offers, setOffers] = useState<MoonetixOffer[]>([]);
  const [currency, setCurrency] = useState("WBC");
  const [usdBdtRate, setUsdBdtRate] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [minimumReward, setMinimumReward] = useState("");
  const [visibleCount, setVisibleCount] = useState(pageSize);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [hidden, setHidden] = useState(false);

  const loadOffers = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await api<MoonetixOffersResponse>(
        "/offers/providers/moonetix/catalog",
        {},
        30_000,
      );
      setOffers(result.offers);
      setCurrency(result.currency);
      setUsdBdtRate(result.usd_bdt_rate);
      setHidden(false);
    } catch (reason: unknown) {
      if (reason instanceof ApiError && reason.status === 404) {
        setHidden(true);
      } else {
        setError(reason instanceof Error ? reason.message : "Moonetix offers could not be loaded.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadOffers();
  }, [loadOffers]);

  const categories = useMemo(
    () => [...new Set(offers.map((offer) => offer.category.toLowerCase()))].sort(),
    [offers],
  );
  const visibleOffers = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    const minReward = Number(minimumReward);
    const hasMinimumReward =
      minimumReward !== "" && Number.isFinite(minReward) && minReward > 0;
    return offers.filter((offer) => {
      const matchesCategory = category === "all" || offer.category.toLowerCase() === category;
      const matchesSearch =
        !query ||
        `${offer.title} ${offer.description} ${offer.category} ${offer.goals.map((goal) => goal.name).join(" ")}`
          .toLocaleLowerCase()
          .includes(query);
      const matchesReward =
        !hasMinimumReward || Number(offer.estimated_user_reward_usd) >= minReward;
      return matchesCategory && matchesSearch && matchesReward;
    });
  }, [category, minimumReward, offers, search]);

  if (hidden) return null;

  return (
    <section className="offerwall-gg moonetix-catalog" aria-labelledby="moonetix-catalog-title">
      <div className="offerwall-gg-heading">
        <div>
          <p className="eyebrow">MOONETIX OFFERS</p>
          <h2 id="moonetix-catalog-title">Complete offers and earn WBC</h2>
          <p className="muted">
            Browse eligible offers. New users only; VPNs and emulators are not allowed.
          </p>
        </div>
        {!error && (
          <span className="offerwall-gg-count" aria-live="polite">
            {loading ? "Loading offers..." : `${visibleOffers.length} of ${offers.length} offers`}
          </span>
        )}
      </div>

      <div className="offerwall-gg-controls">
        <label className="offerwall-gg-search">
          <span className="sr-only">Search Moonetix offers</span>
          <Search aria-hidden="true" size={17} />
          <Input
            type="search"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setVisibleCount(pageSize);
            }}
            placeholder="Search offers"
          />
        </label>
        <label className="offerwall-gg-filter">
          <span>Minimum estimated reward (USD)</span>
          <Input
            type="number"
            min="0"
            step="0.01"
            value={minimumReward}
            onChange={(event) => {
              setMinimumReward(event.target.value);
              setVisibleCount(pageSize);
            }}
            placeholder="Any amount"
          />
        </label>
        {categories.length > 0 && (
          <div className="offerwall-gg-categories" aria-label="Filter Moonetix offers by category">
            {["all", ...categories].map((item) => (
              <button
                aria-pressed={category === item}
                className="offerwall-gg-category"
                key={item}
                onClick={() => {
                  setCategory(item);
                  setVisibleCount(pageSize);
                }}
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
            <Button className="offerwall-gg-retry" onClick={() => void loadOffers()} type="button" variant="outline">
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      ) : loading ? (
        <div className="offerwall-gg-grid" aria-label="Loading Moonetix offers">
          {[0, 1, 2, 3].map((item) => (
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
        <div className="offerwall-gg-grid" aria-label="Moonetix offers">
          {visibleOffers.slice(0, visibleCount).map((offer) => (
            <Card className="offerwall-gg-card moonetix-offer-card" key={offer.id}>
              <div className="offerwall-gg-art">
                {offer.image_url ? (
                  <Image
                    alt=""
                    loading="lazy"
                    referrerPolicy="no-referrer"
                    src={offer.image_url}
                    width={300}
                    height={200}
                    unoptimized
                  />
                ) : (
                  <span className="offerwall-gg-art-icon">{offerIcon(offer.category)}</span>
                )}
                <div className="offerwall-gg-art-badges">
                  <Badge variant="secondary">{offer.category}</Badge>
                  {offer.is_variable && <Badge>Variable reward</Badge>}
                </div>
              </div>
              <CardContent className="offerwall-gg-card-body">
                <CardTitle>{offer.title}</CardTitle>
                <p className="offerwall-gg-description">
                  {offer.description || "Complete the offer requirements to earn a reward."}
                </p>
                {offer.goals.length > 0 && (
                  <p className="offerwall-gg-requirements">
                    <strong>{offer.goals.length} reward {offer.goals.length === 1 ? "step" : "steps"}:</strong>{" "}
                    {offer.goals.slice(0, 2).map((goal) => goal.name).join(" · ")}
                    {offer.goals.length > 2 ? ` · +${offer.goals.length - 2} more` : ""}
                  </p>
                )}
                <div className="offerwall-gg-card-meta">
                  <span>New users only</span>
                  <span>{offer.category}</span>
                </div>
                <div className="offerwall-gg-card-footer">
                  <div className="offerwall-gg-reward">
                    <small>{offer.is_variable ? "EST. WORKBIT REWARD · UP TO" : "EST. WORKBIT REWARD"}</small>
                    <strong>
                      {formatWbcFromUsd(
                        offer.is_variable
                          ? offer.estimated_user_reward_max_usd ?? offer.estimated_user_reward_usd
                          : offer.estimated_user_reward_usd,
                        usdBdtRate,
                      ) ?? formatUsd(offer.estimated_user_reward_usd)}
                    </strong>
                    <small>
                      Moonetix: {offer.is_variable && offer.reward_max
                        ? `up to ${formatProviderReward(offer.reward_max)}`
                        : formatProviderReward(offer.reward)}{" "}
                      {currency}
                    </small>
                  </div>
                  <Button asChild className="offerwall-gg-start" size="sm">
                    <a href={offer.start_url} rel="noopener noreferrer" target="_blank">
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
              : "Moonetix inventory depends on your country and device. Check back later."}
          </span>
        </div>
      )}

      {!error && !loading && visibleCount < visibleOffers.length && (
        <div className="offerwall-gg-more">
          <Button onClick={() => setVisibleCount((count) => count + pageSize)} type="button" variant="outline">
            Load more offers
          </Button>
        </div>
      )}

      <p className="offerwall-gg-note">
        Rewards are estimates based on WorkBit&apos;s active reward policy. Moonetix confirms each completed step before WorkBit credits your wallet.
      </p>
    </section>
  );
}
