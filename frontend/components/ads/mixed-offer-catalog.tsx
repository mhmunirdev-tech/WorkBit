"use client";

import Image from "next/image";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, ArrowUpRight, Clock3, Gamepad2, Search, Smartphone, Sparkles } from "lucide-react";
import { ApiError, api } from "../../lib/api";
import { formatUsd } from "../../lib/utils";
import { Alert, AlertDescription } from "../ui/alert";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import { Skeleton } from "../ui/skeleton";
import { BitcoTasksOfferWall } from "./providers/bitcotasks/wall";

type TheoremReachSurvey = {
  id: string;
  survey_id: number;
  title: string;
  rank: number;
  estimated_time_minutes: number | null;
  user_reward_usd: string;
  entry_url: string;
};

type MoonetixOffer = {
  id: string;
  title: string;
  category: string;
  description: string;
  goals: { name: string }[];
  estimated_user_reward_usd: string;
  estimated_user_reward_max_usd: string | null;
  is_variable: boolean;
  image_url: string | null;
  start_url: string;
};

type OfferwallMeOffer = {
  id: string;
  title: string;
  description: string;
  image_url: string | null;
  devices: string[];
  provider_reward: string;
  reward_name: string;
  estimated_user_reward_usd: string;
  multi_step: boolean;
  click_url: string;
};

type OfferwallGGOffer = {
  id: number;
  title: string;
  description: string;
  requirements: string;
  image_url: string | null;
  categories: string[];
  devices: string[];
  user_reward_usd: string;
  reward_up_to: boolean;
  featured: boolean;
  click_url: string;
};

type OfferwallGGResponse = {
  offers: OfferwallGGOffer[];
  page: number;
  pages: number;
};

type WallTarget =
  | { kind: "iframe"; url: string }
  | { kind: "bitcotasks" };

type MixedOffer = {
  id: string;
  title: string;
  description: string;
  category: string;
  imageUrl: string | null;
  tags: string[];
  rewardUsd: string | null;
  rewardIsMaximum?: boolean;
  estimatedTimeMinutes?: number | null;
  destination:
    | { kind: "link"; url: string }
    | { kind: "wall"; target: WallTarget };
};

type Loaded<T> =
  | { kind: "loaded"; data: T }
  | { kind: "unavailable" }
  | { kind: "failed" };

type OfferwallGroups = {
  surveys: MixedOffer[];
  apps: MixedOffer[];
  partnerOffers: MixedOffer[];
  otherOffers: MixedOffer[];
  hostedWalls: MixedOffer[];
};

const emptyGroups: OfferwallGroups = {
  surveys: [],
  apps: [],
  partnerOffers: [],
  otherOffers: [],
  hostedWalls: [],
};

async function loadSource<T>(path: string): Promise<Loaded<T>> {
  try {
    return { kind: "loaded", data: await api<T>(path) };
  } catch (reason: unknown) {
    if (reason instanceof ApiError && reason.status === 404) {
      return { kind: "unavailable" };
    }
    return { kind: "failed" };
  }
}

function interleave(groups: MixedOffer[][]) {
  const mixed: MixedOffer[] = [];
  for (let index = 0; groups.some((group) => index < group.length); index += 1) {
    for (const group of groups) {
      if (group[index]) mixed.push(group[index]);
    }
  }
  return mixed;
}

function offerIcon(category: string) {
  const normalized = category.toLowerCase();
  if (normalized.includes("game")) return <Gamepad2 aria-hidden="true" />;
  if (normalized.includes("app") || normalized.includes("mobile")) {
    return <Smartphone aria-hidden="true" />;
  }
  if (normalized.includes("survey")) return <Clock3 aria-hidden="true" />;
  return <Sparkles aria-hidden="true" />;
}

export function MixedOfferCatalog() {
  const [groups, setGroups] = useState<OfferwallGroups>(emptyGroups);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasLoadError, setHasLoadError] = useState(false);
  const [search, setSearch] = useState("");
  const [minimumReward, setMinimumReward] = useState("");
  const [activeWall, setActiveWall] = useState<MixedOffer | null>(null);
  const [ggPage, setGgPage] = useState(1);
  const [ggPages, setGgPages] = useState(1);
  const activeWallRef = useRef<HTMLDivElement>(null);

  const loadCatalogs = useCallback(async () => {
    setLoading(true);
    setHasLoadError(false);
    setActiveWall(null);
    const [
      theoremReach,
      moonetix,
      offerwallMe,
      offerwallGG,
      cpxWall,
      bitcoTasks,
      offerwallAd,
    ] = await Promise.all([
      loadSource<{ surveys: TheoremReachSurvey[] }>("/offers/providers/theoremreach/surveys"),
      loadSource<{ offers: MoonetixOffer[] }>("/offers/providers/moonetix/catalog"),
      loadSource<{ offers: OfferwallMeOffer[] }>("/offers/providers/offerwall-me/catalog"),
      loadSource<OfferwallGGResponse>("/offers/providers/offerwall-gg/catalog?page=1&limit=50"),
      loadSource<{ wall_url: string }>("/offers/providers/cpx-research/wall-url"),
      loadSource<{ api_key: string; sub_id: string; sig?: string }>("/offers/providers/bitcotasks/sdk-config"),
      loadSource<{ wall_url: string }>("/offers/providers/offerwall-ad/wall-url"),
    ]);

    const nextGroups: OfferwallGroups = {
      ...emptyGroups,
      surveys: theoremReach.kind === "loaded"
        ? theoremReach.data.surveys.map((survey) => ({
          id: `survey-${survey.id}`,
          title: survey.title,
          description: "Complete an eligible survey and answer the questions honestly.",
          category: "Survey",
          imageUrl: null,
          tags: [
            ...(survey.estimated_time_minutes ? [`${survey.estimated_time_minutes} min`] : []),
            ...(survey.rank > 0 ? [`Rank ${survey.rank}`] : []),
          ],
          rewardUsd: survey.user_reward_usd,
          estimatedTimeMinutes: survey.estimated_time_minutes,
          destination: { kind: "link", url: survey.entry_url },
        }))
        : [],
      apps: moonetix.kind === "loaded"
        ? moonetix.data.offers.map((offer) => ({
          id: `app-${offer.id}`,
          title: offer.title,
          description: [
            offer.description,
            ...offer.goals.slice(0, 2).map((goal) => goal.name),
          ].filter(Boolean).join(" · ") || "Complete the offer requirements to earn a reward.",
          category: offer.category,
          imageUrl: offer.image_url,
          tags: [offer.category, ...(offer.is_variable ? ["Variable reward"] : [])],
          rewardUsd: offer.estimated_user_reward_max_usd ?? offer.estimated_user_reward_usd,
          rewardIsMaximum: offer.is_variable && Boolean(offer.estimated_user_reward_max_usd),
          destination: { kind: "link", url: offer.start_url },
        }))
        : [],
      partnerOffers: offerwallMe.kind === "loaded"
        ? offerwallMe.data.offers.map((offer) => ({
          id: `partner-${offer.id}`,
          title: offer.title,
          description: offer.description || "Complete the offer requirements to earn a reward.",
          category: "Offer",
          imageUrl: offer.image_url,
          tags: [
            ...offer.devices.slice(0, 2),
            ...(offer.multi_step ? ["Multi-step"] : []),
          ],
          rewardUsd: offer.estimated_user_reward_usd,
          destination: { kind: "link", url: offer.click_url },
        }))
        : [],
      otherOffers: offerwallGG.kind === "loaded"
        ? offerwallGG.data.offers.map((offer) => ({
          id: `offer-${offer.id}`,
          title: offer.title,
          description: [
            offer.description,
            ...(offer.requirements ? [`How to qualify: ${offer.requirements}`] : []),
          ].filter(Boolean).join(" · ") || "Complete the offer requirements to earn a reward.",
          category: offer.categories[0] || "Offer",
          imageUrl: offer.image_url,
          tags: [
            ...offer.categories.slice(0, 2),
            ...offer.devices.slice(0, 1),
            ...(offer.featured ? ["Featured"] : []),
          ],
          rewardUsd: offer.user_reward_usd,
          rewardIsMaximum: offer.reward_up_to,
          destination: { kind: "link", url: offer.click_url },
        }))
        : [],
      hostedWalls: [],
    };

    const hostedWalls: MixedOffer[] = [];
    if (cpxWall.kind === "loaded") {
      hostedWalls.push({
        id: "hosted-surveys",
        title: "Browse more surveys",
        description: "Explore additional surveys and check your eligibility.",
        category: "Survey",
        imageUrl: null,
        tags: ["More surveys"],
        rewardUsd: null,
        destination: { kind: "wall", target: { kind: "iframe", url: cpxWall.data.wall_url } },
      });
    }
    if (bitcoTasks.kind === "loaded") {
      hostedWalls.push({
        id: "hosted-tasks",
        title: "Browse tasks and activities",
        description: "Explore available tasks, surveys, videos, and other activities.",
        category: "Tasks",
        imageUrl: null,
        tags: ["Tasks", "Surveys"],
        rewardUsd: null,
        destination: { kind: "wall", target: { kind: "bitcotasks" } },
      });
    }
    if (offerwallAd.kind === "loaded") {
      hostedWalls.push({
        id: "hosted-offers",
        title: "Explore more offers",
        description: "Browse additional eligible activities and offers.",
        category: "Offers",
        imageUrl: null,
        tags: ["More offers"],
        rewardUsd: null,
        destination: { kind: "wall", target: { kind: "iframe", url: offerwallAd.data.wall_url } },
      });
    }

    if (theoremReach.kind === "unavailable") {
      const theoremReachWall = await loadSource<{ wall_url: string }>(
        "/offers/providers/theoremreach/wall-url",
      );
      if (theoremReachWall.kind === "loaded") {
        hostedWalls.push({
          id: "hosted-opinions",
          title: "Browse more surveys",
          description: "Explore additional surveys and check your eligibility.",
          category: "Survey",
          imageUrl: null,
          tags: ["More surveys"],
          rewardUsd: null,
          destination: {
            kind: "wall",
            target: { kind: "iframe", url: theoremReachWall.data.wall_url },
          },
        });
      }
      if (theoremReachWall.kind === "failed") setHasLoadError(true);
    }

    const failedSources = [
      theoremReach,
      moonetix,
      offerwallMe,
      offerwallGG,
      cpxWall,
      bitcoTasks,
      offerwallAd,
    ].filter((source) => source.kind === "failed").length;
    if (failedSources > 0) setHasLoadError(true);
    nextGroups.hostedWalls = hostedWalls;
    setGroups(nextGroups);
    setGgPage(offerwallGG.kind === "loaded" ? offerwallGG.data.page : 1);
    setGgPages(offerwallGG.kind === "loaded" ? offerwallGG.data.pages : 1);
    setLoading(false);
  }, []);

  useEffect(() => {
    void loadCatalogs();
  }, [loadCatalogs]);

  useEffect(() => {
    if (activeWall) {
      activeWallRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [activeWall]);

  const mixedOffers = useMemo(
    () => interleave([
      groups.surveys,
      groups.apps,
      groups.partnerOffers,
      groups.otherOffers,
      groups.hostedWalls,
    ]),
    [groups],
  );
  const visibleOffers = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    const minReward = Number(minimumReward);
    const hasMinimumReward = minimumReward !== "" && Number.isFinite(minReward) && minReward > 0;
    return mixedOffers.filter((offer) => {
      const matchesSearch =
        !query ||
        `${offer.title} ${offer.description} ${offer.category} ${offer.tags.join(" ")}`
          .toLocaleLowerCase()
          .includes(query);
      const matchesMinimumReward =
        !hasMinimumReward ||
        (offer.rewardUsd !== null && Number(offer.rewardUsd) >= minReward);
      return matchesSearch && matchesMinimumReward;
    });
  }, [minimumReward, mixedOffers, search]);

  const loadMoreOffers = useCallback(async () => {
    setLoadingMore(true);
    setHasLoadError(false);
    try {
      const result = await api<OfferwallGGResponse>(
        `/offers/providers/offerwall-gg/catalog?page=${ggPage + 1}&limit=50`,
      );
      const moreOffers: MixedOffer[] = result.offers.map((offer) => ({
        id: `offer-${offer.id}`,
        title: offer.title,
        description: [
          offer.description,
          ...(offer.requirements ? [`How to qualify: ${offer.requirements}`] : []),
        ].filter(Boolean).join(" · ") || "Complete the offer requirements to earn a reward.",
        category: offer.categories[0] || "Offer",
        imageUrl: offer.image_url,
        tags: [
          ...offer.categories.slice(0, 2),
          ...offer.devices.slice(0, 1),
          ...(offer.featured ? ["Featured"] : []),
        ],
        rewardUsd: offer.user_reward_usd,
        rewardIsMaximum: offer.reward_up_to,
        destination: { kind: "link", url: offer.click_url },
      }));
      setGroups((current) => ({
        ...current,
        otherOffers: [...current.otherOffers, ...moreOffers],
      }));
      setGgPage(result.page);
      setGgPages(result.pages);
    } catch {
      setHasLoadError(true);
    } finally {
      setLoadingMore(false);
    }
  }, [ggPage]);

  const activeWallTarget =
    activeWall?.destination.kind === "wall" ? activeWall.destination.target : null;

  return (
    <div className="mixed-offers">
      <div className="offerwall-gg-controls mixed-offer-controls">
        <label className="offerwall-gg-search">
          <span className="sr-only">Search all offers</span>
          <Search aria-hidden="true" size={17} />
          <Input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
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
            onChange={(event) => setMinimumReward(event.target.value)}
            placeholder="Any amount"
          />
        </label>
        <span className="mixed-offer-count" aria-live="polite">
          {loading
            ? "Loading offers..."
            : `${visibleOffers.length} ${visibleOffers.length === 1 ? "offer" : "offers"}`}
        </span>
      </div>

      {hasLoadError && (
        <Alert className="offerwall-gg-error" variant="destructive">
          <AlertDescription>
            Some offers could not be loaded. Please retry.
            <Button className="offerwall-gg-retry" onClick={() => void loadCatalogs()} type="button" variant="outline">
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {loading ? (
        <div className="mixed-offer-grid" aria-label="Loading offers">
          {[0, 1, 2, 3, 4].map((item) => (
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
        <div className="mixed-offer-grid" aria-label="All available offers">
          {visibleOffers.map((offer) => (
            <Card className="offerwall-gg-card" key={offer.id}>
              <div className="offerwall-gg-art">
                {offer.imageUrl ? (
                  <Image
                    alt=""
                    loading="lazy"
                    referrerPolicy="no-referrer"
                    src={offer.imageUrl}
                    width={300}
                    height={200}
                    unoptimized
                  />
                ) : (
                  <span className="offerwall-gg-art-icon">{offerIcon(offer.category)}</span>
                )}
                <div className="offerwall-gg-art-badges">
                  <Badge variant="secondary">{offer.category}</Badge>
                </div>
              </div>
              <CardContent className="offerwall-gg-card-body">
                <CardTitle>{offer.title}</CardTitle>
                <p className="offerwall-gg-description">{offer.description}</p>
                {(offer.tags.length > 0 || offer.estimatedTimeMinutes) && (
                  <div className="offerwall-gg-card-meta">
                    {offer.tags.slice(0, 3).map((tag) => <span key={tag}>{tag}</span>)}
                    {offer.estimatedTimeMinutes && (
                      <span>{offer.estimatedTimeMinutes} min</span>
                    )}
                  </div>
                )}
                <div className="offerwall-gg-card-footer">
                  <div className="offerwall-gg-reward">
                    {offer.rewardUsd ? (
                      <>
                        <small>{offer.rewardIsMaximum ? "EST. REWARD · UP TO" : "EST. REWARD"}</small>
                        <strong>{formatUsd(offer.rewardUsd)}</strong>
                      </>
                    ) : (
                      <>
                        <small>AVAILABLE ACTIVITIES</small>
                        <strong>Browse</strong>
                      </>
                    )}
                  </div>
                  {offer.destination.kind === "link" ? (
                    <Button asChild className="offerwall-gg-start" size="sm">
                      <a href={offer.destination.url} rel="noopener noreferrer" target="_blank">
                        Start offer <ArrowUpRight aria-hidden="true" size={15} />
                      </a>
                    </Button>
                  ) : (
                    <Button
                      className="offerwall-gg-start"
                      onClick={() => setActiveWall(offer)}
                      size="sm"
                      type="button"
                    >
                      Browse offers <ArrowUpRight aria-hidden="true" size={15} />
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="offerwall-gg-empty">
          <Sparkles aria-hidden="true" />
          <strong>{mixedOffers.length ? "No matching offers" : "No offers available right now"}</strong>
          <span>{mixedOffers.length ? "Try a different search or reward filter." : "Check back later for new offers."}</span>
        </div>
      )}

      {!loading && ggPage < ggPages && (
        <div className="offerwall-gg-more">
          <Button disabled={loadingMore} onClick={() => void loadMoreOffers()} type="button" variant="outline">
            {loadingMore ? "Loading..." : "Load more offers"}
          </Button>
        </div>
      )}

      {activeWall && activeWallTarget && (
        <div className="mixed-offer-wall" ref={activeWallRef}>
          <Button onClick={() => setActiveWall(null)} type="button" variant="outline">
            <ArrowLeft aria-hidden="true" size={15} /> Back to offers
          </Button>
          {activeWallTarget.kind === "bitcotasks" ? (
            <BitcoTasksOfferWall />
          ) : (
            <article className="offerwall-gg mixed-offer-wall-frame">
              <iframe
                className="offerwall-ad-frame"
                loading="lazy"
                referrerPolicy="strict-origin-when-cross-origin"
                src={activeWallTarget.url}
                title={activeWall.title}
              />
            </article>
          )}
        </div>
      )}
    </div>
  );
}
