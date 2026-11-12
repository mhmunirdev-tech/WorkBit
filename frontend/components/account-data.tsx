"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import { useLiveRefresh } from "../lib/use-live-refresh";
import { formatUsd, formatWbcFromUsd, WBC_VALUE_BDT } from "../lib/utils";
import { Shell, WALLET_UPDATED_EVENT } from "./shell";
import { Alert, AlertDescription } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Skeleton } from "./ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { WithdrawalPage } from "./withdrawals";

type Wallet = {
  available_balance: string;
  deposit_balance: string;
  earning_balance: string;
  package_active: boolean;
  can_deposit: boolean;
  pending_balance: string;
  lifetime_earned: string;
  lifetime_withdrawn: string;
  currency: string;
  usd_bdt_rate: string | null;
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
  return formatUsd(value);
}

function balanceAmount(value: string, rate: string | null) {
  return formatWbcFromUsd(value, rate) ?? formatUsd(value);
}

function useAccountData<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const refresh = useCallback(async () => {
    try {
      setData(await api<T>(path));
      setError("");
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Account data could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    void refresh();
  }, [refresh]);
  useLiveRefresh(refresh, { eventName: WALLET_UPDATED_EVENT });

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
  const {
    data: transactions,
    loading: transactionsLoading,
    error: transactionsError,
  } = useAccountData<Transaction[]>("/wallet/transactions");
  const recentRewards = (transactions ?? [])
    .filter((item) => item.type.startsWith("OFFER_REWARD"))
    .slice(0, 5);

  return <Shell><header className="top"><div><p className="eyebrow">YOUR WALLET</p><h1>Balances and ledger</h1><p className="muted">Earning balance can be withdrawn. To buy a package, choose it first and pay its listed price by bKash or Nagad.</p></div><div className="welcome-actions">{data?.can_deposit && <Button className="dashboard-cta deposit-cta" variant="outline" asChild><Link href="/packages">Choose a package</Link></Button>}<Button className="dashboard-cta withdraw-cta" asChild><Link href="/withdraw">Withdraw</Link></Button><Button className="primary dashboard-cta" asChild><Link href="/transactions">View transactions</Link></Button></div></header>
    <PageState loading={loading} error={error} empty={!data}>{data && <><section className="stats">
      {[
        ["Available balance", data.available_balance, "Ready to use or withdraw"],
        ["Deposit balance", data.deposit_balance, "Package purchases only"],
        ["Earning balance", data.earning_balance, "Withdrawable or usable for packages"],
        ["Pending rewards", data.pending_balance, "Awaiting provider confirmation"],
        ["Total earned", data.lifetime_earned, "Ledger-recorded"],
        ["Total withdrawn", data.lifetime_withdrawn, "Completed withdrawals"],
      ].map(([title, value, note]) => <Card className="stat" asChild key={title}><article><p>{title}</p><h2>{balanceAmount(value, data.usd_bdt_rate)}</h2><small>{note}</small></article></Card>)}
    </section>
    <Card className="panel reward-list wallet-recent-rewards">
      <div className="panel-head">
        <div>
          <h2>Recent rewards</h2>
          <p>See each offer reward, its status, and both USD and WBC amounts.</p>
        </div>
        <Link href="/transactions">View all</Link>
      </div>
      {transactionsError ? (
        <Alert className="state error-state" variant="destructive" role="alert">
          <AlertDescription>{transactionsError}</AlertDescription>
        </Alert>
      ) : transactionsLoading ? (
        <div aria-live="polite"><Skeleton className="mt-4 h-14 w-full" /></div>
      ) : recentRewards.length ? (
        <div className="mt-3">
          {recentRewards.map((item) => (
            <article className="reward-row flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between" key={item.id}>
              <div>
                <strong>{item.description || "Offer reward"}</strong>
                <small className="block">
                  {formatUsd(item.amount, { minimumFractionDigits: 2 })}
                  {" · "}
                  {formatWbcFromUsd(item.amount, data.usd_bdt_rate) ?? "WBC estimate unavailable"}
                </small>
                <small className="block">{new Date(item.created_at).toLocaleString()}</small>
              </div>
              <Badge className="status-badge self-start sm:self-auto" variant="outline">{item.status}</Badge>
            </article>
          ))}
        </div>
      ) : (
        <p className="mt-4 text-sm text-muted-foreground">Your offer reward activity will appear here.</p>
      )}
    </Card>
    <Card className="panel wallet-note"><h2>How your wallet works</h2><p><strong>1 WBC = ৳{WBC_VALUE_BDT.toFixed(2)}.</strong> Your WBC balance is the BDT equivalent of your USD wallet, calculated using the current USD/BDT withdrawal rate and the WBC value above. Your underlying wallet and ledger remain in USD, so the displayed WBC amount can change when the admin exchange rate changes. Approved deposits can only be used for earning packages and are not withdrawable. Approved earnings can be withdrawn or used for a package. Each package stays active for the duration shown in the package catalog when you purchase it.</p><Link href="/rewards">Review reward decisions →</Link></Card></>}</PageState>
    <WithdrawalPage embedded />
  </Shell>;
}

export function TransactionsPage() {
  const { data, loading, error } = useAccountData<Transaction[]>("/wallet/transactions");
  const { data: wallet } = useAccountData<Wallet>("/wallet");
  return <Shell><header className="top"><div><p className="eyebrow">WALLET LEDGER</p><h1>Earnings history</h1><p className="muted">Append-only records of wallet activity. Referral rewards are shown in WBC using the current exchange rate.</p></div></header>
    <PageState loading={loading} error={error} empty={!data?.length}>{data && data.length > 0 && <Card className="panel table-panel"><Table className="ledger-table" aria-label="Wallet transactions"><TableHeader><TableRow className="ledger-heading"><TableHead>Transaction</TableHead><TableHead>Amount</TableHead><TableHead>Status</TableHead><TableHead>Created</TableHead></TableRow></TableHeader><TableBody>{data.map((item) => {
      const isReferralReward = item.type === "REFERRAL_REWARD_APPROVAL";
      const displayedAmount = isReferralReward
        ? formatWbcFromUsd(item.amount, wallet?.usd_bdt_rate) ?? amount(item.amount, item.currency)
        : amount(item.amount, item.currency);
      return <TableRow className="ledger-row" key={item.id}><TableCell><strong>{item.description || item.type.replaceAll("_", " ")}</strong><small>{item.type.replaceAll("_", " ")}</small></TableCell><TableCell><strong>{displayedAmount}</strong></TableCell><TableCell><Badge className="status-badge" variant="outline">{item.status}</Badge></TableCell><TableCell><time dateTime={item.created_at}>{new Date(item.created_at).toLocaleString()}</time></TableCell></TableRow>;
    })}</TableBody></Table></Card>}</PageState>
  </Shell>;
}

export function RewardsPage() {
  const { data, loading, error } = useAccountData<Reward[]>("/rewards");
  const { data: wallet } = useAccountData<Wallet>("/wallet");
  return <Shell><header className="top"><div><p className="eyebrow">REWARD HISTORY</p><h1>Your rewards</h1><p className="muted">Verified provider rewards are shown as WBC equivalents at the current USD/BDT rate. Provider payout amounts and the underlying wallet ledger remain in USD.</p></div></header>
    <PageState loading={loading} error={error} empty={!data?.length}>{data && data.length > 0 && <Card className="panel reward-list">{data.map((item) => <article className="reward-row" key={item.id}><div><strong>{formatWbcFromUsd(item.user_reward, wallet?.usd_bdt_rate) ?? amount(item.user_reward, item.currency)}</strong><small>Provider payout {amount(item.provider_payout, item.currency)} · {new Date(item.created_at).toLocaleString()}</small></div><Badge className="status-badge" variant="outline">{item.status}</Badge></article>)}</Card>}</PageState>
  </Shell>;
}
