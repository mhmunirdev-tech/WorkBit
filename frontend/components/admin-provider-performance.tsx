"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity } from "lucide-react";
import { api } from "../lib/api";
import { useLiveRefresh } from "../lib/use-live-refresh";
import { Alert, AlertDescription } from "./ui/alert";
import { Card } from "./ui/card";

type ProviderPerformance = {
  provider: string;
  conversions: number;
  approved: number;
  pending: number;
  reversed: number;
  approval_rate: number;
  approved_provider_payout_usd: string;
  approved_user_rewards_usd: string;
  pending_user_rewards_usd: string;
  reversed_user_rewards_usd: string;
};

function usd(value: string) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(Number(value));
}

function providerName(slug: string) {
  return slug.split(/[-_]/).map((part) => part[0]?.toUpperCase() + part.slice(1)).join(" ");
}

export function AdminProviderPerformance() {
  const [providers, setProviders] = useState<ProviderPerformance[] | null>(null);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      setProviders(await api<ProviderPerformance[]>("/analytics/admin/provider-performance"));
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Provider performance could not be loaded.");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);
  useLiveRefresh(refresh, { intervalMs: 30_000 });

  return (
    <main className="admin-provider-performance">
      <header className="admin-dashboard-header">
        <div>
          <p className="eyebrow">OFFER PROVIDERS</p>
          <h1>Provider performance</h1>
          <p>USD totals are based on provider-confirmed conversion records.</p>
        </div>
        <div className="admin-dashboard-live"><span />Refreshes every 30 seconds</div>
      </header>

      {error && <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}

      <Card className="admin-provider-panel">
        <div className="admin-section-heading">
          <div><p className="eyebrow">REWARD CONVERSIONS</p><h2>By provider</h2></div>
          <Activity size={18} aria-hidden="true" />
        </div>
        {providers === null ? (
          <p className="admin-analytics-empty">Loading provider performance…</p>
        ) : providers.length === 0 ? (
          <p className="admin-analytics-empty">No provider conversions have been recorded yet.</p>
        ) : (
          <div className="admin-provider-table-wrap">
            <table className="admin-provider-table">
              <thead>
                <tr>
                  <th scope="col">Provider</th>
                  <th scope="col">Conversions</th>
                  <th scope="col">Approved</th>
                  <th scope="col">Pending</th>
                  <th scope="col">Reversed</th>
                  <th scope="col">Approval rate</th>
                  <th scope="col">Provider payout</th>
                  <th scope="col">User rewards</th>
                  <th scope="col">Pending rewards</th>
                  <th scope="col">Reversed rewards</th>
                </tr>
              </thead>
              <tbody>
                {providers.map((provider) => (
                  <tr key={provider.provider}>
                    <th scope="row">{providerName(provider.provider)}</th>
                    <td>{provider.conversions.toLocaleString()}</td>
                    <td>{provider.approved.toLocaleString()}</td>
                    <td>{provider.pending.toLocaleString()}</td>
                    <td>{provider.reversed.toLocaleString()}</td>
                    <td>{provider.approval_rate.toFixed(2)}%</td>
                    <td>{usd(provider.approved_provider_payout_usd)}</td>
                    <td>{usd(provider.approved_user_rewards_usd)}</td>
                    <td>{usd(provider.pending_user_rewards_usd)}</td>
                    <td>{usd(provider.reversed_user_rewards_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="admin-provider-footnote">
          Approval rate excludes conversions still awaiting a final decision. Reversed totals include reversed, charged-back, and fraud-marked rewards.
        </p>
      </Card>
    </main>
  );
}
