"use client";

import Image from "next/image";
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

type OfferwallMeOffer = {
  id: string;
  provider: string;
  title: string;
  description: string;
  image_url: string | null;
  devices: string[];
  countries: string[];
  provider_reward: string;
  reward_name: string;
  provider_payout_usd: string;
  estimated_user_reward_usd: string;
  multi_step: boolean;
  click_url: string;
};

type OfferwallMeOffersResponse = {
  offers: OfferwallMeOffer[];
  total: number;
};

const pageSize = 50;

function offerIcon(offer: OfferwallMeOffer) {
  const devices = offer.devices.join(" ").toLowerCase();
  if (devices.includes("android") || devices.includes("mobile")) {
    return <Smartphone aria-hidden="true" />;
  }
  if (offer.multi_step) return <Gamepad2 aria-hidden="true" />;
  return <Sparkles aria-hidden="true" />;
}

function formatProviderReward(value: string) {
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function OfferwallMeWall() {
  const [offers, setOffers] = useState<OfferwallMeOffer[]>([]);
  const [search, setSearch] = useState("");
  const [device, setDevice] = useState("all");
  const [minimumReward, setMinimumReward] = useState("");
  const [visibleCount, setVisibleCount] = useState(pageSize);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [hidden, setHidden] = useState(false);

  const loadOffers = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await api<OfferwallMeOffersResponse>(
        "/offers/providers/offerwall-me/catalog",
      );
      setOffers(result.offers);
    } catch (reason: unknown) {
      if (reason instanceof ApiError && reason.status === 404) {
        setHidden(true);
      } else {
        setError(
          reason instanceof Error
            ? reason.message
            : "Offerwall.me offers could not be loaded.",
        );
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadOffers();
  }, [loadOffers]);

  const devices = useMemo(
    () =>
      [...new Set(offers.flatMap((offer) => offer.devices.map((item) => item.toLowerCase())))].sort(),
    [offers],
  );
  const visibleOffers = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    const minReward = Number(minimumReward);
    const hasMinimumReward =
      minimumReward !== "" && Number.isFinite(minReward) && minReward > 0;
    return offers.filter((offer) => {
      const matchesSearch =
        !query ||
        `${offer.title} ${offer.description} ${offer.provider} ${offer.devices.join(" ")}`
          .toLocaleLowerCase()
          .includes(query);
      const matchesDevice =
        device === "all" || offer.devices.some((item) => item.toLowerCase() === device);
      const matchesReward =
        !hasMinimumReward ||
        Number(offer.estimated_user_reward_usd) >= minReward;
      return matchesSearch && matchesDevice && matchesReward;
    });
  }, [device, minimumReward, offers, search]);

  if (hidden) return null;

  return (
    <section className="offerwall-gg" aria-labelledby="offerwall-me-title">
      <div className="offerwall-gg-heading">
        <div>
          <p className="eyebrow">OFFERWALL.ME OFFERS</p>
          <h2 id="offerwall-me-title">More ways to earn</h2>
          <p className="muted">
            Browse available offers without leaving WorkBit. Eligibility and final rewards depend on each offer&apos;s terms.
          </p>
        </div>
        {!error && (
          <span className="offerwall-gg-count" aria-live="polite">
            {loading ? "Loading offers..." : `${Math.min(visibleCount, visibleOffers.length)} of ${visibleOffers.length} offers`}
          </span>
        )}
      </div>

      <div className="offerwall-gg-controls">
        <label className="offerwall-gg-search">
          <span className="sr-only">Search Offerwall.me offers</span>
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
        {devices.length > 0 && (
          <label className="offerwall-gg-filter">
            <span>Supported device</span>
            <select
              value={device}
              onChange={(event) => {
                setDevice(event.target.value);
                setVisibleCount(pageSize);
              }}
            >
              <option value="all">All devices</option>
              {devices.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      {error ? (
        <Alert className="offerwall-gg-error" variant="destructive">
          <AlertDescription>
            <span>{error}</span>
            <Button
              className="offerwall-gg-retry"
              onClick={() => void loadOffers()}
              type="button"
              variant="outline"
            >
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      ) : loading ? (
        <div className="offerwall-gg-grid" aria-label="Loading Offerwall.me offers">
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
        <div className="offerwall-gg-grid" aria-label="Offerwall.me offers">
          {visibleOffers.slice(0, visibleCount).map((offer) => (
            <Card className="offerwall-gg-card" key={offer.id}>
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
                  <span className="offerwall-gg-art-icon">{offerIcon(offer)}</span>
                )}
                <div className="offerwall-gg-art-badges">
                  <Badge variant="secondary">{offer.provider}</Badge>
                  {offer.multi_step && <Badge>Multi-step</Badge>}
                </div>
              </div>
              <CardContent className="offerwall-gg-card-body">
                <CardTitle>{offer.title}</CardTitle>
                <p className="offerwall-gg-description">
                  {offer.description || "Complete the offer requirements to earn a reward."}
                </p>
                <div className="offerwall-gg-card-meta">
                  <span>{offer.devices.slice(0, 2).join(" · ") || "Device varies"}</span>
                  <span>{offer.countries.slice(0, 3).join(" · ") || "Country varies"}</span>
                </div>
                <div className="offerwall-gg-card-footer">
                  <div className="offerwall-gg-reward">
                    <small>EST. WORKBIT REWARD</small>
                    <strong>{formatUsd(offer.estimated_user_reward_usd)}</strong>
                    <small>
                      Offerwall.me: {formatProviderReward(offer.provider_reward)}{" "}
                      {offer.reward_name}
                    </small>
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
              ? "Try a different search or device."
              : "Check back later; Offerwall.me inventory changes based on your country and device."}
          </span>
        </div>
      )}
      {!error && !loading && visibleCount < visibleOffers.length && (
        <div className="offerwall-gg-more">
          <Button
            onClick={() => setVisibleCount((count) => count + pageSize)}
            type="button"
            variant="outline"
          >
            Load more offers
          </Button>
        </div>
      )}

      <p className="offerwall-gg-note">
        Rewards shown are estimated from WorkBit&apos;s active reward policy. Provider verification is required before rewards are credited.
      </p>
    </section>
  );
}
