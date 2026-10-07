"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api } from "../lib/api";
import { Shell, ShellUser } from "./shell";
import { Alert, AlertDescription } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Skeleton } from "./ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";

type Amount = string | number;

type WithdrawalRecord = {
  id: string;
  amount: Amount;
  currency: string;
  method: string;
  destination_hint: string;
  status: string;
  created_at: string;
  updated_at: string;
};

type Summary = {
  available_balance: Amount;
  currency: string;
  user: ShellUser;
  withdrawal_summary: {
    enabled: boolean;
    minimum_amount: Amount;
    pending_request: WithdrawalRecord | null;
    last_request: WithdrawalRecord | null;
  };
};

function formatMoney(value: Amount, currency: string) {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(Number(value));
}

function readableStatus(status: string) {
  return status.toLocaleLowerCase().replaceAll("_", " ");
}

function useWithdrawalData() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [records, setRecords] = useState<WithdrawalRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [summaryError, setSummaryError] = useState("");
  const [historyError, setHistoryError] = useState("");

  useEffect(() => {
    let active = true;
    Promise.allSettled([
      api<Summary>("/dashboard"),
      api<WithdrawalRecord[]>("/withdrawals"),
    ]).then(([summaryResult, historyResult]) => {
      if (!active) return;
      if (summaryResult.status === "fulfilled") setSummary(summaryResult.value);
      else setSummaryError(summaryResult.reason instanceof Error ? summaryResult.reason.message : "Your wallet summary could not be loaded.");
      if (historyResult.status === "fulfilled") setRecords(historyResult.value);
      else setHistoryError(historyResult.reason instanceof Error ? historyResult.reason.message : "Withdrawal history could not be loaded.");
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => {
      active = false;
    };
  }, []);

  return {
    summary,
    records,
    setRecords,
    loading,
    summaryError,
    historyError,
    setHistoryError,
  };
}

function WithdrawalHistory({ records, currency }: { records: WithdrawalRecord[]; currency: string }) {
  if (records.length === 0) {
    return (
      <div className="dashboard-empty">
        <strong>No withdrawal requests</strong>
        <span>When you submit a request, its review status will appear here.</span>
        <Link href="/withdraw">Review withdrawal requirements</Link>
      </div>
    );
  }

  return (
    <div className="withdrawal-table-wrap">
      <Table className="withdrawal-table">
        <TableHeader><TableRow><TableHead scope="col">Request</TableHead><TableHead scope="col">Amount</TableHead><TableHead scope="col">Status</TableHead><TableHead scope="col">Submitted</TableHead></TableRow></TableHeader>
        <TableBody>
          {records.map((record) => (
            <TableRow key={record.id}>
              <TableCell><strong>Manual payout</strong><small>{record.destination_hint}</small></TableCell>
              <TableCell>{formatMoney(record.amount, currency)}</TableCell>
              <TableCell><Badge className={`withdrawal-status withdrawal-${record.status.toLowerCase()}`} variant="outline">{readableStatus(record.status)}</Badge></TableCell>
              <TableCell><time dateTime={record.created_at}>{new Date(record.created_at).toLocaleString()}</time></TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

export function WithdrawalPage({ historyOnly = false }: { historyOnly?: boolean }) {
  const {
    summary,
    records,
    setRecords,
    loading,
    summaryError,
    historyError,
    setHistoryError,
  } = useWithdrawalData();
  const [amount, setAmount] = useState("");
  const [destination, setDestination] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [messageIsError, setMessageIsError] = useState(false);
  const canWithdraw = Boolean(
    summary?.withdrawal_summary.enabled &&
    !summary.withdrawal_summary.pending_request &&
    Number(summary.available_balance) >= Number(summary.withdrawal_summary.minimum_amount)
  );

  async function submitRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setMessage("");
    setMessageIsError(false);
    try {
      const request = await api<WithdrawalRecord>("/withdrawals", {
        method: "POST",
        body: JSON.stringify({ amount, destination }),
      });
      setRecords((existing) => [request, ...existing]);
      setDestination("");
      setAmount("");
      setMessage("Your withdrawal request was submitted for manual review.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "The withdrawal request could not be submitted.");
      setMessageIsError(true);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <Shell user={summary?.user}>
        <section className="withdrawal-loading" aria-busy="true" aria-label="Loading withdrawal information">
          <Skeleton className="h-5 w-1/2" /><Skeleton className="h-4 w-1/3" />
          <Card className="panel skeleton"><Skeleton className="h-5 w-1/2" /><Skeleton className="h-20 w-full" /></Card>
        </section>
      </Shell>
    );
  }

  return (
    <Shell user={summary?.user}>
      <header className="top">
        <div>
          <p className="eyebrow">{historyOnly ? "WALLET" : "MANUAL PAYOUT"}</p>
          <h1>{historyOnly ? "Withdrawal history" : "Withdraw funds"}</h1>
          <p className="muted">
            {historyOnly
              ? "Review the current status of your payout requests."
              : "Requests are reviewed manually. WorkBit never pays out more than your available wallet balance."}
          </p>
        </div>
        <Button className="text-link" variant="link" asChild><Link href="/wallet">View wallet →</Link></Button>
      </header>

      {summaryError && <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{summaryError}</AlertDescription></Alert>}
      {summary && (
        <>
          <section className="withdrawal-summary-grid">
            <Card className="dashboard-metric" asChild><article><p>Available balance</p><h2>{formatMoney(summary.available_balance, summary.currency)}</h2><small>Authoritative backend wallet value</small></article></Card>
            <Card className="dashboard-metric" asChild><article><p>Minimum request</p><h2>{formatMoney(summary.withdrawal_summary.minimum_amount, summary.currency)}</h2><small>Configured by WorkBit</small></article></Card>
            <Card className="dashboard-metric" asChild><article><p>Latest request</p><h2 className="withdrawal-latest-value">{summary.withdrawal_summary.last_request ? readableStatus(summary.withdrawal_summary.last_request.status) : "None"}</h2><small>{summary.withdrawal_summary.last_request ? new Date(summary.withdrawal_summary.last_request.created_at).toLocaleDateString() : "No prior payout request"}</small></article></Card>
          </section>

          {!historyOnly && (
            <Card className="panel withdrawal-form-panel">
              <div className="panel-heading">
                <div><p className="eyebrow">SECURE REQUEST</p><h2>Request a manual payout</h2><p className="panel-subtitle">Payout details are encrypted at rest. Only authorized withdrawal reviewers can view them.</p></div>
              </div>
              {!summary.withdrawal_summary.enabled ? (
                <div className="state withdrawal-disabled" role="status">Withdrawals are disabled until WorkBit's secure payout encryption key is configured.</div>
              ) : summary.withdrawal_summary.pending_request ? (
                <div className="state withdrawal-disabled" role="status">You have a {readableStatus(summary.withdrawal_summary.pending_request.status)} request. Wait for it to be resolved before submitting another.</div>
              ) : Number(summary.available_balance) < Number(summary.withdrawal_summary.minimum_amount) ? (
                <div className="state withdrawal-disabled" role="status">Your available balance has not reached the configured minimum. Earn and verify more rewards before requesting a payout.</div>
              ) : (
                <form className="withdrawal-form" onSubmit={submitRequest}>
                  <Label>
                    Amount ({summary.currency})
                    <Input
                      name="amount"
                      type="number"
                      inputMode="decimal"
                      min={String(summary.withdrawal_summary.minimum_amount)}
                      max={String(summary.available_balance)}
                      step="0.00000001"
                      required
                      value={amount}
                      onChange={(event) => setAmount(event.target.value)}
                    />
                    <small>Available: {formatMoney(summary.available_balance, summary.currency)}</small>
                  </Label>
                  <Label>
                    Payout destination
                    <Input
                      name="destination"
                      type="text"
                      autoComplete="off"
                      minLength={6}
                      maxLength={512}
                      required
                      value={destination}
                      onChange={(event) => setDestination(event.target.value)}
                      placeholder="Account email or payout identifier"
                    />
                    <small>Use an account you control. This value is encrypted and only shown to authorized reviewers.</small>
                  </Label>
                  <Button className="primary" type="submit" disabled={!canWithdraw || submitting}>
                    {submitting ? "Submitting request…" : "Submit payout request"}
                  </Button>
                </form>
              )}
              {message && <Alert className={`inline-status${messageIsError ? " is-error" : ""}`} variant={messageIsError ? "destructive" : "default"} role={messageIsError ? "alert" : "status"}><AlertDescription>{message}</AlertDescription></Alert>}
            </Card>
          )}

          <Card className="panel withdrawal-history-panel">
            <div className="panel-heading"><div><p className="eyebrow">REQUEST RECORDS</p><h2>{historyOnly ? "All requests" : "Recent requests"}</h2></div>{!historyOnly && <Button className="text-link" variant="link" asChild><Link href="/withdrawals">View all →</Link></Button>}</div>
            {historyError ? <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{historyError}</AlertDescription></Alert> : <WithdrawalHistory records={historyOnly ? records : records.slice(0, 5)} currency={summary.currency} />}
          </Card>
        </>
      )}
    </Shell>
  );
}
