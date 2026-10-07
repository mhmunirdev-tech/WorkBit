"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Shell } from "./shell";
import { Alert, AlertDescription } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Skeleton } from "./ui/skeleton";

type Wallet = {
  available_balance: string;
  pending_balance: string;
  lifetime_earned: string;
  lifetime_withdrawn: string;
  currency: string;
};
type Transaction = {
  id: string;
  type: string;
  amount: string;
  currency: string;
  status: string;
  description: string;
  created_at: string;
};
type Reward = {
  id: string;
  conversion_id: string;
  provider_payout: string;
  user_reward: string;
  currency: string;
  status: string;
  created_at: string;
};

function amount(value: string, currency: string) {
  return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(Number(value));
}

function useAccountData<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    api<T>(path)
      .then((result) => { if (active) setData(result); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Account data could not be loaded."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [path]);
  return { data, loading, error };
}

function PageState({ loading, error, empty, children }: { loading: boolean; error: string; empty: boolean; children: React.ReactNode }) {
  if (loading) return <Card className="panel" aria-live="polite"><Skeleton className="h-5 w-1/2" /><p>Loading account records…</p></Card>;
  if (error) return <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{error} <Link href="/login">Sign in</Link></AlertDescription></Alert>;
  if (empty) return <Card className="panel empty"><strong>No records yet</strong><span>Validated account activity will appear here when it exists.</span></Card>;
  return <>{children}</>;
}

export function WalletPage() {
  const { data, loading, error } = useAccountData<Wallet>("/wallet");
  return <Shell><header className="top"><div><p className="eyebrow">YOUR WALLET</p><h1>Balances and ledger</h1><p className="muted">Wallet values are read from the backend projection.</p></div><Button className="primary dashboard-cta" asChild><Link href="/transactions">View transactions</Link></Button></header>
    <PageState loading={loading} error={error} empty={!data}>{data && <><section className="stats">
      {[
        ["Available", data.available_balance, "Available balance"],
        ["Pending", data.pending_balance, "Awaiting provider confirmation"],
        ["Lifetime earned", data.lifetime_earned, "Ledger-recorded"],
        ["Lifetime withdrawn", data.lifetime_withdrawn, "Completed withdrawals"],
      ].map(([title, value, note]) => <article className="stat" key={title}><p>{title}</p><h2>{amount(value, data.currency)}</h2><small>{note}</small></article>)}
    </section>    <Card className="panel wallet-note"><h2>How your wallet works</h2><p>New eligible rewards can remain pending while provider confirmation is outstanding. Only approved rewards become available. Each balance movement is backed by a wallet ledger transaction.</p><Link href="/rewards">Review reward decisions →</Link></Card></>}</PageState>
  </Shell>;
}

export function TransactionsPage() {
  const { data, loading, error } = useAccountData<Transaction[]>("/wallet/transactions");
  return <Shell><header className="top"><div><p className="eyebrow">WALLET LEDGER</p><h1>Transactions</h1><p className="muted">Append-only records of movements that affect your wallet.</p></div></header>
    <PageState loading={loading} error={error} empty={!data?.length}>{data && data.length > 0 && <Card className="panel table-panel"><div className="ledger-table" role="table" aria-label="Wallet transactions"><div className="ledger-row ledger-heading" role="row"><span>Transaction</span><span>Amount</span><span>Status</span><span>Created</span></div>{data.map((item) => <div className="ledger-row" role="row" key={item.id}><span><strong>{item.description || item.type.replaceAll("_", " ")}</strong><small>{item.type.replaceAll("_", " ")}</small></span><strong>{amount(item.amount, item.currency)}</strong><Badge className="status-badge" variant="outline">{item.status}</Badge><time dateTime={item.created_at}>{new Date(item.created_at).toLocaleString()}</time></div>)}</div></Card>}</PageState>
  </Shell>;
}

export function RewardsPage() {
  const { data, loading, error } = useAccountData<Reward[]>("/rewards");
  return <Shell><header className="top"><div><p className="eyebrow">REWARD HISTORY</p><h1>Your rewards</h1><p className="muted">Reward decisions linked to provider-reported conversions.</p></div></header>
    <PageState loading={loading} error={error} empty={!data?.length}>{data && data.length > 0 && <Card className="panel reward-list">{data.map((item) => <article className="reward-row" key={item.id}><div><strong>{amount(item.user_reward, item.currency)}</strong><small>Provider payout {amount(item.provider_payout, item.currency)} · {new Date(item.created_at).toLocaleString()}</small></div><Badge className="status-badge" variant="outline">{item.status}</Badge></article>)}</Card>}</PageState>
  </Shell>;
}
