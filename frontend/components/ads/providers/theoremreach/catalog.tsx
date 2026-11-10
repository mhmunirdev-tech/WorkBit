"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowUpRight, Clock3, Search, Sparkles } from "lucide-react";
import { ApiError, api } from "../../../../lib/api";
import { formatUsd } from "../../../../lib/utils";
import { Alert, AlertDescription } from "../../../ui/alert";
import { Badge } from "../../../ui/badge";
import { Button } from "../../../ui/button";
import { Card, CardContent, CardTitle } from "../../../ui/card";
import { Input } from "../../../ui/input";
import { Skeleton } from "../../../ui/skeleton";

type TheoremReachSurvey = {
  id: string;
  survey_id: number;
  title: string;
  rank: number;
  estimated_time_minutes: number | null;
  incidence: string | null;
  user_reward_usd: string;
  entry_url: string;
};

type TheoremReachSurveysResponse = {
  surveys: TheoremReachSurvey[];
};

type TheoremReachWallResponse = {
  wall_url: string;
};

export function TheoremReachSurveyCatalog() {
  const [surveys, setSurveys] = useState<TheoremReachSurvey[]>([]);
  const [search, setSearch] = useState("");
  const [minimumReward, setMinimumReward] = useState("");
  const [maximumTime, setMaximumTime] = useState("");
  const [error, setError] = useState("");
  const [wallUrl, setWallUrl] = useState("");
  const [hidden, setHidden] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api<TheoremReachSurveysResponse>("/offers/providers/theoremreach/surveys")
      .then((result) => {
        if (active) setSurveys(result.surveys);
      })
      .catch(async (reason: unknown) => {
        if (!active) return;
        if (reason instanceof ApiError && reason.status === 404) {
          try {
            const result = await api<TheoremReachWallResponse>(
              "/offers/providers/theoremreach/wall-url",
            );
            if (active) setWallUrl(result.wall_url);
          } catch (fallbackReason: unknown) {
            if (!active) return;
            if (fallbackReason instanceof ApiError && fallbackReason.status === 404) {
              setHidden(true);
              return;
            }
            setError(fallbackReason instanceof Error ? fallbackReason.message : "TheoremReach surveys could not be loaded.");
          }
          return;
        }
        setError(reason instanceof Error ? reason.message : "TheoremReach surveys could not be loaded.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const visibleSurveys = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    const minReward = Number(minimumReward);
    const maxTime = Number(maximumTime);
    const hasMinimumReward =
      minimumReward !== "" && Number.isFinite(minReward) && minReward > 0;
    const hasMaximumTime =
      maximumTime !== "" && Number.isFinite(maxTime) && maxTime > 0;
    return surveys.filter((survey) => {
      const matchesSearch =
        !query || `${survey.title} ${survey.survey_id}`.toLocaleLowerCase().includes(query);
      const matchesReward =
        !hasMinimumReward || Number(survey.user_reward_usd) >= minReward;
      const matchesTime =
        !hasMaximumTime ||
        (survey.estimated_time_minutes !== null &&
          survey.estimated_time_minutes <= maxTime);
      return matchesSearch && matchesReward && matchesTime;
    });
  }, [maximumTime, minimumReward, search, surveys]);

  if (hidden) return null;

  if (wallUrl) {
    return (
      <section className="theoremreach-wall" aria-labelledby="theoremreach-surveys-title">
        <div className="theoremreach-wall-heading">
          <div>
            <p className="eyebrow">THEOREMREACH SURVEYS</p>
            <h2 id="theoremreach-surveys-title">Share your opinion and earn</h2>
            <p className="muted">
              Survey availability and completion rewards are determined by TheoremReach.
            </p>
          </div>
        </div>
        <iframe
          className="theoremreach-wall-frame"
          loading="lazy"
          referrerPolicy="strict-origin-when-cross-origin"
          src={wallUrl}
          title="TheoremReach surveys"
        />
        <p className="theoremreach-wall-note">
          Only verified server callbacks credit survey rewards to your WorkBit wallet.
        </p>
      </section>
    );
  }

  return (
    <section className="offerwall-gg" aria-labelledby="theoremreach-surveys-title">
      <div className="offerwall-gg-heading">
        <div>
          <p className="eyebrow">THEOREMREACH SURVEYS</p>
          <h2 id="theoremreach-surveys-title">Share your opinion and earn</h2>
          <p className="muted">
            Browse available surveys without leaving WorkBit. Eligibility and final rewards depend on your profile.
          </p>
        </div>
        {!error && (
          <span className="offerwall-gg-count" aria-live="polite">
            {loading ? "Loading surveys..." : `${visibleSurveys.length} of ${surveys.length} surveys`}
          </span>
        )}
      </div>
      {surveys.length > 0 && (
        <div className="offerwall-gg-controls theoremreach-survey-controls">
          <label className="offerwall-gg-search theoremreach-survey-search">
            <span className="sr-only">Search TheoremReach surveys</span>
            <Search aria-hidden="true" size={17} />
            <Input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search surveys"
            />
          </label>
          <label className="offerwall-gg-filter">
            <span>Minimum reward (USD)</span>
            <Input type="number" min="0" step="0.01" value={minimumReward} onChange={(event) => setMinimumReward(event.target.value)} placeholder="Any amount" />
          </label>
          <label className="offerwall-gg-filter">
            <span>Maximum time (minutes)</span>
            <Input type="number" min="1" max="1440" step="1" value={maximumTime} onChange={(event) => setMaximumTime(event.target.value)} placeholder="Any duration" />
          </label>
        </div>
      )}
      {error ? (
        <Alert className="offerwall-gg-error" variant="destructive">
          <AlertDescription>
            <span>{error}</span>
          </AlertDescription>
        </Alert>
      ) : loading ? (
        <div className="offerwall-gg-grid" aria-label="Loading TheoremReach surveys">
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
      ) : visibleSurveys.length > 0 ? (
        <div className="offerwall-gg-grid" aria-label="TheoremReach surveys">
          {visibleSurveys.map((survey) => (
            <Card className="offerwall-gg-card" key={survey.id}>
              <div className="offerwall-gg-art theoremreach-survey-art">
                <span className="offerwall-gg-art-icon"><Sparkles aria-hidden="true" /></span>
                <div className="offerwall-gg-art-badges">
                  <Badge variant="secondary">TheoremReach</Badge>
                  {survey.rank > 0 && <Badge>Rank {survey.rank}</Badge>}
                </div>
              </div>
              <CardContent className="offerwall-gg-card-body">
                <CardTitle>{survey.title}</CardTitle>
                <p className="offerwall-gg-description">
                  Complete an eligible survey and answer the questions honestly. TheoremReach verifies completion.
                </p>
                <div className="offerwall-gg-card-meta">
                  <span>
                    <Clock3 aria-hidden="true" size={14} />
                    {survey.estimated_time_minutes
                      ? `${survey.estimated_time_minutes} min`
                      : "Time varies"}
                  </span>
                </div>
                <div className="offerwall-gg-card-footer">
                  <div className="offerwall-gg-reward">
                    <small>EST. YOUR REWARD</small>
                    <strong>{formatUsd(survey.user_reward_usd)}</strong>
                  </div>
                  <Button asChild className="offerwall-gg-start" size="sm">
                    <a href={survey.entry_url} rel="noopener noreferrer" target="_blank">
                      Start survey <ArrowUpRight aria-hidden="true" size={15} />
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
          <strong>{surveys.length ? "No matching surveys" : "No surveys available right now"}</strong>
          <span>
            {surveys.length
              ? "Try a different search."
              : "Survey availability depends on your country and profile. Check back later."}
          </span>
        </div>
      )}
      <p className="offerwall-gg-note">
        Rewards are estimates. Survey eligibility and completion are verified by TheoremReach before WorkBit credits your wallet.
      </p>
    </section>
  );
}
