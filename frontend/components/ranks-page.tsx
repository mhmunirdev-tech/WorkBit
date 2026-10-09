"use client";

import { useEffect, useMemo, useState } from "react";
import { Award, Crown, Layers, Medal, RefreshCw, Search, Trophy } from "lucide-react";
import { api } from "../lib/api";
import { Shell } from "./shell";
import { Alert, AlertDescription } from "./ui/alert";
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Skeleton } from "./ui/skeleton";
import styles from "./ranks-page.module.css";

type RankTier = {
  name: string;
  threshold: string | number;
};

type RankMember = {
  position: number;
  full_name: string;
  avatar_url: string | null;
  rank: string;
  qualifying_value: string | number;
  referrals: number;
};

type RanksData = {
  currency: string;
  tiers: RankTier[];
  current_user: {
    full_name: string;
    avatar_url: string | null;
    position: number | null;
    rank: string;
    qualifying_value: string | number;
    next_rank: string | null;
    next_threshold: string | number | null;
    amount_to_next: string | number;
  };
  leaderboard: RankMember[];
};

type Tab = "leaderboard" | "category";
type SortBy = "rank" | "name";

function formatMoney(value: string | number, currency: string) {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(Number(value));
}

function rankStyle(rank: string) {
  return styles[`rank${rank}`] ?? styles.rankStarter;
}

function initials(name: string) {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "WB";
}

export function RanksPage() {
  const [data, setData] = useState<RanksData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<Tab>("leaderboard");
  const [sortBy, setSortBy] = useState<SortBy>("rank");
  const [search, setSearch] = useState("");

  async function loadRanks() {
    setLoading(true);
    setError("");
    try {
      setData(await api<RanksData>("/ranks"));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Ranks could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadRanks();
  }, []);

  const members = useMemo(() => {
    const normalizedSearch = search.trim().toLocaleLowerCase();
    const filtered = (data?.leaderboard ?? [])
      .filter((member) => member.full_name.toLocaleLowerCase().includes(normalizedSearch));
    if (sortBy === "name") {
      filtered.sort((left, right) => left.full_name.localeCompare(right.full_name));
    }
    return filtered;
  }, [data, search, sortBy]);

  const currentTierIndex = data?.tiers.findIndex(
    (tier) => tier.name === data.current_user.rank,
  ) ?? 0;
  const currentThreshold = Number(data?.tiers[currentTierIndex]?.threshold ?? 0);
  const nextThreshold = Number(data?.current_user.next_threshold ?? 0);
  const progress = data?.current_user.next_rank
    ? Math.min(100, Math.max(0, (
      (Number(data.current_user.qualifying_value) - currentThreshold)
      / (nextThreshold - currentThreshold)
    ) * 100))
    : 100;

  return (
    <Shell>
      <div className={styles.page}>
        <header className={styles.heading}>
          <div>
            <p className="eyebrow">WORKBIT / RECOGNITION</p>
            <h1>Ranks</h1>
            <p className="muted">Ranks are earned automatically through approved ads and completed package purchases.</p>
          </div>
          <Button
            className={styles.refresh}
            variant="outline"
            type="button"
            onClick={() => void loadRanks()}
            disabled={loading}
            aria-label="Refresh ranks"
          >
            <RefreshCw size={16} className={loading ? styles.spinning : undefined} />
          </Button>
        </header>

        {error && <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}
        {loading && !data && (
          <Card className={`panel ${styles.loading}`} aria-busy="true" aria-label="Loading ranks">
            <Skeleton className="h-5 w-1/3" />
            <Skeleton className="h-4 w-2/3" />
          </Card>
        )}

        {data && (
          <>
            <Card className={`panel ${styles.yourRank}`}>
              <div className={styles.yourRankIdentity}>
                <Avatar className={styles.avatar}>
                  {data.current_user.avatar_url && <AvatarImage src={data.current_user.avatar_url} alt="" />}
                  <AvatarFallback>{initials(data.current_user.full_name)}</AvatarFallback>
                </Avatar>
                <div>
                  <p className={styles.overline}>YOUR CURRENT RANK</p>
                  <h2>{data.current_user.rank}</h2>
                  <span>{data.current_user.position ? `Leaderboard #${data.current_user.position}` : "Not currently listed"}</span>
                </div>
              </div>
              <div className={styles.rankProgress}>
                <div className={styles.progressLabels}>
                  <span>{formatMoney(data.current_user.qualifying_value, data.currency)} qualifying activity</span>
                  {data.current_user.next_rank
                    ? <span>{formatMoney(data.current_user.amount_to_next, data.currency)} to {data.current_user.next_rank}</span>
                    : <span>Top rank achieved</span>}
                </div>
                <div
                  className={styles.progressTrack}
                  role="progressbar"
                  aria-label="Progress to next rank"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={Math.round(progress)}
                >
                  <span style={{ width: `${progress}%` }} />
                </div>
              </div>
            </Card>

            <div className={styles.toolbar}>
              <div className={styles.tabs} role="tablist" aria-label="Rank views">
                <button
                  type="button"
                  role="tab"
                  aria-selected={tab === "leaderboard"}
                  className={tab === "leaderboard" ? styles.selectedTab : ""}
                  onClick={() => setTab("leaderboard")}
                >
                  <Trophy size={15} /> Leaderboard
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={tab === "category"}
                  className={tab === "category" ? styles.selectedTab : ""}
                  onClick={() => setTab("category")}
                >
                  <Layers size={15} /> Category Rank
                </button>
              </div>
              {tab === "leaderboard" && (
                <div className={styles.filters}>
                  <label className={styles.sortLabel}>
                    <span className={styles.visuallyHidden}>Sort leaderboard</span>
                    <select value={sortBy} onChange={(event) => setSortBy(event.target.value as SortBy)}>
                      <option value="rank">By rank</option>
                      <option value="name">By name</option>
                    </select>
                  </label>
                  <label className={styles.search}>
                    <Search size={16} aria-hidden="true" />
                    <span className={styles.visuallyHidden}>Search members by name</span>
                    <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by name..." />
                  </label>
                </div>
              )}
            </div>

            {tab === "leaderboard" ? (
              <Card className={`panel ${styles.tableCard}`}>
                <div className={styles.tableScroll}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th scope="col">Rank</th>
                        <th scope="col">Member</th>
                        <th scope="col">Badge</th>
                        <th scope="col">Qualifying activity</th>
                        <th scope="col">Referrals</th>
                      </tr>
                    </thead>
                    <tbody>
                      {members.map((member) => (
                        <tr key={`${member.position}-${member.full_name}`}>
                          <td><span className={`${styles.position} ${member.position <= 3 ? styles[`position${member.position}`] : ""}`}>#{member.position}</span></td>
                          <td>
                            <div className={styles.member}>
                              <Avatar className={styles.memberAvatar}>
                                {member.avatar_url && <AvatarImage src={member.avatar_url} alt="" />}
                                <AvatarFallback>{initials(member.full_name)}</AvatarFallback>
                              </Avatar>
                              <strong>{member.full_name}</strong>
                            </div>
                          </td>
                          <td><span className={`${styles.badge} ${rankStyle(member.rank)}`}><Award size={13} /> {member.rank}</span></td>
                          <td className={styles.value}>{formatMoney(member.qualifying_value, data.currency)}</td>
                          <td className={styles.value}>{member.referrals}</td>
                        </tr>
                      ))}
                      {members.length === 0 && (
                        <tr><td colSpan={5} className={styles.empty}>No members match your search.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </Card>
            ) : (
              <section className={styles.tiers} aria-label="Rank categories">
                {data.tiers.map((tier, index) => {
                  const isCurrent = tier.name === data.current_user.rank;
                  const achieved = Number(data.current_user.qualifying_value) >= Number(tier.threshold);
                  const TierIcon = index === data.tiers.length - 1 ? Crown : index > 0 ? Medal : Award;
                  return (
                    <Card className={`panel ${styles.tierCard}${isCurrent ? ` ${styles.currentTier}` : ""}`} key={tier.name}>
                      <span className={`${styles.tierIcon} ${rankStyle(tier.name)}`}><TierIcon size={20} /></span>
                      <p className={styles.overline}>RANK {String(index + 1).padStart(2, "0")}</p>
                      <h2>{tier.name}</h2>
                      <p className={styles.threshold}>From {formatMoney(tier.threshold, data.currency)}</p>
                      <span className={`${styles.tierStatus}${achieved ? ` ${styles.achieved}` : ""}`}>
                        {isCurrent ? "YOUR RANK" : achieved ? "ACHIEVED" : "NOT YET ACHIEVED"}
                      </span>
                    </Card>
                  );
                })}
              </section>
            )}
            <p className={styles.note}>
              Rank value includes approved USD ad rewards and completed USD package purchases. Pending or reversed activity does not count.
              {" "}Package purchases will count once package checkout is available.
            </p>
          </>
        )}
      </div>
    </Shell>
  );
}
