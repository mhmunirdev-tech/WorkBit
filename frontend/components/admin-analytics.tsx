"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity, Eye, KeyRound, ShieldAlert, Users } from "lucide-react";
import { api } from "../lib/api";
import { useLiveRefresh } from "../lib/use-live-refresh";
import { Alert, AlertDescription } from "./ui/alert";
import { Card } from "./ui/card";

type AdminAnalyticsData = {
  active_visitors: number;
  unique_visitors_today: number;
  page_views_today: number;
  failed_logins_24h: number;
  recent_failed_logins: {
    login_type: string | null;
    email_masked: string | null;
    ip_fingerprint: string | null;
    created_at: string;
  }[];
  daily: {
    date: string;
    unique_visitors: number;
    page_views: number;
    failed_logins: number;
  }[];
};

export function AdminAnalytics() {
  const [analytics, setAnalytics] = useState<AdminAnalyticsData | null>(null);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      setAnalytics(await api<AdminAnalyticsData>("/analytics/admin"));
      setError("");
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Security analytics could not be loaded.");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);
  useLiveRefresh(refresh, { intervalMs: 30_000 });

  const trendDays = analytics?.daily.slice(-14) ?? [];
  const maximumDailyVisitors = Math.max(1, ...trendDays.map((day) => day.unique_visitors));

  return (
    <main className="admin-analytics-page">
      <header className="admin-dashboard-header">
        <div>
          <p className="eyebrow">TRAFFIC & SECURITY</p>
          <h1>Live analytics</h1>
          <p>Visitor activity, traffic history and failed sign-in attempts.</p>
        </div>
        <div className="admin-dashboard-live"><span />Refreshes every 30 seconds</div>
      </header>

      {error && <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}

      <section className="admin-dashboard-metrics admin-analytics-metrics" aria-label="Traffic and security metrics">
        <Card className="admin-dashboard-metric" asChild><article>
          <div className="admin-metric-heading"><span className="admin-metric-icon admin-icon-green"><Activity size={18} /></span><small>LAST 5 MINUTES</small></div>
          <p>Visitors online</p>
          <strong>{analytics ? analytics.active_visitors.toLocaleString() : "—"}</strong>
          <small className="admin-metric-foot">Unique browsers active recently</small>
        </article></Card>
        <Card className="admin-dashboard-metric" asChild><article>
          <div className="admin-metric-heading"><span className="admin-metric-icon admin-icon-blue"><Users size={18} /></span><small>TODAY</small></div>
          <p>Unique visitors</p>
          <strong>{analytics ? analytics.unique_visitors_today.toLocaleString() : "—"}</strong>
          <small className="admin-metric-foot">Privacy-preserving browser IDs</small>
        </article></Card>
        <Card className="admin-dashboard-metric" asChild><article>
          <div className="admin-metric-heading"><span className="admin-metric-icon admin-icon-violet"><Eye size={18} /></span><small>TODAY</small></div>
          <p>Page views</p>
          <strong>{analytics ? analytics.page_views_today.toLocaleString() : "—"}</strong>
          <small className="admin-metric-foot">Repeat views grouped within 30 seconds</small>
        </article></Card>
        <Card className="admin-dashboard-metric" asChild><article>
          <div className="admin-metric-heading"><span className="admin-metric-icon admin-icon-amber"><ShieldAlert size={18} /></span><small>LAST 24 HOURS</small></div>
          <p>Failed login attempts</p>
          <strong>{analytics ? analytics.failed_logins_24h.toLocaleString() : "—"}</strong>
          <small className="admin-metric-foot">User and administrator sign-in failures</small>
        </article></Card>
      </section>

      <section className="admin-analytics-panels">
        <Card className="admin-analytics-panel">
          <div className="admin-section-heading">
            <div><p className="eyebrow">90-DAY HISTORY</p><h2>Visitors / failed logins</h2></div>
          </div>
          {analytics ? (
            <div className="admin-analytics-trend" role="img" aria-label="Daily unique visitors and failed logins over the last 14 days">
              {trendDays.map((day) => {
                const width = day.unique_visitors ? Math.max(4, (day.unique_visitors / maximumDailyVisitors) * 100) : 0;
                return (
                  <div className="admin-analytics-trend-row" key={day.date}>
                    <time dateTime={day.date}>{new Date(`${day.date}T00:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</time>
                    <span className="admin-analytics-bar-track"><span className="admin-analytics-bar" style={{ width: `${width}%` }} /></span>
                    <strong title={`${day.unique_visitors} unique visitors; ${day.failed_logins} failed logins`}>
                      {day.unique_visitors} / {day.failed_logins}
                    </strong>
                  </div>
                );
              })}
            </div>
          ) : <p className="admin-analytics-empty">Loading traffic history…</p>}
        </Card>

        <Card className="admin-analytics-panel">
          <div className="admin-section-heading">
            <div><p className="eyebrow">SECURITY MONITOR</p><h2>Recent failed logins</h2></div>
            <KeyRound size={17} aria-hidden="true" />
          </div>
          {!analytics ? (
            <p className="admin-analytics-empty">Loading security events…</p>
          ) : analytics.recent_failed_logins.length === 0 ? (
            <p className="admin-analytics-empty">No failed login attempts in the last 24 hours.</p>
          ) : (
            <div className="admin-login-events" role="table" aria-label="Recent failed login attempts">
              {analytics.recent_failed_logins.map((event, index) => (
                <div className="admin-login-event" role="row" key={`${event.created_at}-${index}`}>
                  <div><strong>{event.email_masked ?? "Unknown account"}</strong><small>{event.login_type === "admin" ? "Admin sign-in" : "User sign-in"}</small></div>
                  <div><time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time><small>{event.ip_fingerprint ? `IP fingerprint ${event.ip_fingerprint}` : "IP unavailable"}</small></div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </section>
      <p className="admin-analytics-privacy">Visitor identifiers and IP addresses are stored as keyed hashes. Login records show masked email addresses and are automatically purged after 90 days.</p>
    </main>
  );
}
