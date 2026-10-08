"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowUpRight, Banknote, ImagePlus, ShieldCheck, Users } from "lucide-react";
import { api } from "../lib/api";
import { Alert, AlertDescription } from "./ui/alert";
import { Button } from "./ui/button";
import { Card } from "./ui/card";

type AdminDashboardData = {
  total_users: number;
  active_users: number;
  pending_verification: number;
  total_wallet_balance: string;
  currency: string;
};

type Withdrawal = {
  id: string;
  amount: string | number;
  currency: string;
  destination_hint: string;
  status: string;
  created_at: string;
};

function formatMoney(amount: string | number, currency: string): string {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(Number(amount));
}

export function AdminDashboard() {
  const [data, setData] = useState<AdminDashboardData | null>(null);
  const [withdrawals, setWithdrawals] = useState<Withdrawal[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      api<AdminDashboardData>("/admin/dashboard"),
      api<Withdrawal[]>("/admin/withdrawals"),
    ])
      .then(([dashboard, requests]) => {
        setData(dashboard);
        setWithdrawals(requests);
      })
      .catch((loadError: unknown) => {
        setError(loadError instanceof Error ? loadError.message : "Admin dashboard could not be loaded.");
      });
  }, []);

  const pendingWithdrawals = withdrawals.filter(
    (request) => request.status === "PENDING" || request.status === "PROCESSING",
  );

  return (
    <main className="admin-dashboard-page">
      <header className="admin-dashboard-header">
        <div>
          <p className="eyebrow">PLATFORM OVERVIEW</p>
          <h1>Good to see you, Admin</h1>
          <p>Here’s what’s happening across WorkBit today.</p>
        </div>
        <div className="admin-dashboard-header-actions">
          <Button variant="outline" asChild><Link href="/admin/banners"><ImagePlus size={16} /> Manage banners</Link></Button>
          <div className="admin-dashboard-live"><span />Live platform data</div>
        </div>
      </header>

      {error && (
        <Alert className="state error-state" variant="destructive" role="alert">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <section className="admin-dashboard-metrics" aria-label="Platform overview">
        <Card className="admin-dashboard-metric" asChild><article>
          <div className="admin-metric-heading"><span className="admin-metric-icon admin-icon-blue"><Users size={18} /></span><small>ALL TIME</small></div>
          <p>Total users</p>
          <strong>{data ? data.total_users.toLocaleString() : "—"}</strong>
          <small className="admin-metric-foot">Registered WorkBit accounts</small>
        </article></Card>
        <Card className="admin-dashboard-metric" asChild><article>
          <div className="admin-metric-heading"><span className="admin-metric-icon admin-icon-green"><ShieldCheck size={18} /></span><small>ACTIVE</small></div>
          <p>Active users</p>
          <strong>{data ? data.active_users.toLocaleString() : "—"}</strong>
          <small className="admin-metric-foot">{data && data.total_users ? `${Math.round(data.active_users / data.total_users * 100)}% of all accounts` : "Accounts currently active"}</small>
        </article></Card>
        <Card className="admin-dashboard-metric" asChild><article>
          <div className="admin-metric-heading"><span className="admin-metric-icon admin-icon-amber"><Users size={18} /></span><small>NEEDS ATTENTION</small></div>
          <p>Pending verification</p>
          <strong>{data ? data.pending_verification.toLocaleString() : "—"}</strong>
          <small className="admin-metric-foot">Accounts awaiting email verification</small>
        </article></Card>
        <Card className="admin-dashboard-metric" asChild><article>
          <div className="admin-metric-heading"><span className="admin-metric-icon admin-icon-violet"><Banknote size={18} /></span><small>USER WALLETS</small></div>
          <p>Available balance</p>
          <strong>{data ? formatMoney(data.total_wallet_balance, data.currency) : "—"}</strong>
          <small className="admin-metric-foot">Combined available wallet funds</small>
        </article></Card>
      </section>

      <section className="admin-dashboard-lower">
        <Card className="admin-dashboard-queue">
          <div className="admin-section-heading">
            <div><p className="eyebrow">PAYOUT OPERATIONS</p><h2>Withdrawal queue</h2></div>
            <Button variant="link" asChild><Link href="/admin/withdrawals">View all <ArrowUpRight size={14} /></Link></Button>
          </div>
          <div className="admin-queue-summary">
            <strong>{pendingWithdrawals.length}</strong>
            <span>requests need review or payment</span>
          </div>
          {pendingWithdrawals.length === 0 ? (
            <p className="admin-queue-empty">You’re all caught up. There are no outstanding withdrawal requests.</p>
          ) : (
            <div className="admin-queue-list">
              {pendingWithdrawals.slice(0, 5).map((request) => (
                <Link className="admin-queue-row" href="/admin/withdrawals" key={request.id}>
                  <span className="admin-queue-avatar"><Banknote size={16} /></span>
                  <span className="admin-queue-copy">
                    <strong>{formatMoney(request.amount, request.currency)}</strong>
                    <small>{request.destination_hint} · {new Date(request.created_at).toLocaleDateString()}</small>
                  </span>
                  <span className={`admin-queue-status status-${request.status.toLowerCase()}`}>{request.status.toLowerCase()}</span>
                  <ArrowUpRight className="admin-queue-arrow" size={16} />
                </Link>
              ))}
            </div>
          )}
        </Card>

        <Card className="admin-dashboard-shortcut">
          <span className="admin-shortcut-icon"><Banknote size={19} /></span>
          <p className="eyebrow">QUICK ACTION</p>
          <h2>Review payouts</h2>
          <p>Open the manual withdrawal workspace to inspect destinations and process requests.</p>
          <Button className="primary" asChild>
            <Link href="/admin/withdrawals">Go to withdrawals <ArrowUpRight size={15} /></Link>
          </Button>
        </Card>
      </section>
      <footer className="admin-dashboard-footer">WorkBit operations console <span>·</span> User account data is updated from the backend.</footer>
    </main>
  );
}
