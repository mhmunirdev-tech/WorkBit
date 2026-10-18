"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { showInvalidFieldToast, showToast } from "../lib/toast";
import { formatUsd } from "../lib/utils";
import { Shell, ShellUser } from "./shell";
import { Alert, AlertDescription } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Skeleton } from "./ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";

type Amount = string | number;

type WithdrawalRecord = {
  id: string;
  amount: Amount;
  currency: string;
  payout_amount: Amount | null;
  payout_currency: string | null;
  exchange_rate: Amount | null;
  method: string;
  destination_hint: string;
  status: string;
  payment_transaction_id: string | null;
  paid_at: string | null;
  created_at: string;
  updated_at: string;
};

type Summary = {
  available_balance: Amount;
  withdrawable_balance: Amount;
  currency: string;
  user: ShellUser;
  withdrawal_summary: {
    enabled: boolean;
    minimum_amount: Amount;
    usd_bdt_rate: Amount | null;
    pending_request: WithdrawalRecord | null;
    last_request: WithdrawalRecord | null;
  };
};

function formatMoney(value: Amount, currency: string) {
  return formatUsd(value);
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
  const active = useRef(false);

  const refresh = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true);
    const [summaryResult, historyResult] = await Promise.allSettled([
      api<Summary>("/dashboard"),
      api<WithdrawalRecord[]>("/withdrawals"),
    ]);
    if (!active.current) return;
    if (summaryResult.status === "fulfilled") {
      setSummary(summaryResult.value);
      setSummaryError("");
    } else {
      setSummary(null);
      setSummaryError(summaryResult.reason instanceof Error ? summaryResult.reason.message : "Your wallet summary could not be loaded.");
    }
    if (historyResult.status === "fulfilled") {
      setRecords(historyResult.value);
      setHistoryError("");
    } else {
      setRecords([]);
      setHistoryError(historyResult.reason instanceof Error ? historyResult.reason.message : "Withdrawal history could not be loaded.");
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    active.current = true;
    void refresh(true);
    return () => {
      active.current = false;
    };
  }, [refresh]);

  return {
    summary,
    records,
    setRecords,
    loading,
    refresh,
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
        <Link href="/wallet#withdraw-request">Review withdrawal requirements</Link>
      </div>
    );
  }

  return (
    <div className="withdrawal-table-wrap">
      <Table className="withdrawal-table">
        <TableHeader><TableRow><TableHead scope="col">Request</TableHead><TableHead scope="col">Wallet debit</TableHead><TableHead scope="col">Payout</TableHead><TableHead scope="col">Status</TableHead><TableHead scope="col">Submitted</TableHead></TableRow></TableHeader>
        <TableBody>
          {records.map((record) => (
            <TableRow key={record.id}>
              <TableCell>
                <strong>{record.method === "MANUAL" ? "Manual payout" : record.method}</strong>
                <small>{record.destination_hint}</small>
                {record.payment_transaction_id && <small>Payment reference: {record.payment_transaction_id}</small>}
              </TableCell>
              <TableCell>{formatMoney(record.amount, currency)}</TableCell>
              <TableCell>{record.payout_amount != null && record.payout_currency ? formatMoney(record.payout_amount, record.payout_currency) : "—"}</TableCell>
              <TableCell><Badge className={`withdrawal-status withdrawal-${record.status.toLowerCase()}`} variant="outline">{readableStatus(record.status)}</Badge></TableCell>
              <TableCell><time dateTime={record.created_at}>{new Date(record.created_at).toLocaleString()}</time></TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

export function WithdrawalPage({
  historyOnly = false,
  embedded = false,
}: {
  historyOnly?: boolean;
  embedded?: boolean;
}) {
  const {
    summary,
    records,
    setRecords,
    loading,
    refresh,
    summaryError,
    historyError,
    setHistoryError,
  } = useWithdrawalData();
  const [amount, setAmount] = useState("");
  const [destination, setDestination] = useState("");
  const [paymentMethod, setPaymentMethod] = useState<"BKASH" | "NAGAD">("BKASH");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [messageIsError, setMessageIsError] = useState(false);
  const normalizedDestination = destination
    .replace(/[\s()-]/g, "")
    .replace(/^\+?880/, "0");
  const canWithdraw = Boolean(
    summary?.withdrawal_summary.enabled &&
    !summary.withdrawal_summary.pending_request &&
    Number(summary.withdrawable_balance) >= Number(summary.withdrawal_summary.minimum_amount) &&
    Number(amount) >= Number(summary.withdrawal_summary.minimum_amount) &&
    Number(amount) <= Number(summary.withdrawable_balance) &&
    /^01[3-9]\d{8}$/.test(normalizedDestination)
  );
  const estimatedPayout = summary?.withdrawal_summary.usd_bdt_rate && amount
    ? Number(amount) * Number(summary.withdrawal_summary.usd_bdt_rate)
    : null;

  useEffect(() => {
    if (!summary) return;
    const { withdrawal_summary: settings } = summary;
    if (!settings.enabled) {
      showToast({
        title: "Withdrawals unavailable",
        description: "Withdrawals are disabled until payout settings are configured.",
        variant: "destructive",
      });
    } else if (settings.pending_request) {
      showToast({
        title: "Withdrawal request pending",
        description: "Resolve your existing request before submitting another.",
        variant: "default",
      });
    } else if (Number(summary.withdrawable_balance) < Number(settings.minimum_amount)) {
      showToast({
        title: "Minimum withdrawal not reached",
        description: "Your withdrawable earnings have not reached the minimum request amount.",
        variant: "default",
      });
    }
  }, [summary]);

  async function submitRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setMessage("");
    setMessageIsError(false);
    try {
      const request = await api<WithdrawalRecord>("/withdrawals", {
        method: "POST",
        body: JSON.stringify({ amount, destination, payment_method: paymentMethod }),
      });
      setRecords((existing) => [request, ...existing]);
      setDestination("");
      setAmount("");
      const successMessage = "Your withdrawal request was submitted for manual review.";
      setMessage(successMessage);
      showToast({
        title: "Withdrawal request submitted",
        description: successMessage,
        variant: "success",
      });
      await refresh();
    } catch (error) {
      const message = error instanceof Error ? error.message : "The withdrawal request could not be submitted.";
      setMessage(message);
      setMessageIsError(true);
      showToast({
        title: "Withdrawal request failed",
        description: message,
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    const loadingContent = (
      <section className="withdrawal-loading" aria-busy="true" aria-label="Loading withdrawal information">
        <Skeleton className="h-5 w-1/2" /><Skeleton className="h-4 w-1/3" />
        <Card className="panel skeleton"><Skeleton className="h-5 w-1/2" /><Skeleton className="h-20 w-full" /></Card>
      </section>
    );
    if (embedded) return <div className="wallet-withdrawal-management">{loadingContent}</div>;
    return <Shell user={summary?.user}>{loadingContent}</Shell>;
  }

  const content = (
    <>
      {!embedded && <header className="top">
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
      </header>}

      {summaryError && <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{summaryError}</AlertDescription></Alert>}
      {summary && (
        <>
          {!embedded && <section className="withdrawal-summary-grid">
            <Card className="dashboard-metric" asChild><article><p>Withdrawable earnings</p><h2>{formatMoney(summary.withdrawable_balance, summary.currency)}</h2><small>Deposit balance is reserved for packages</small></article></Card>
            <Card className="dashboard-metric" asChild><article><p>Minimum request</p><h2>{formatMoney(summary.withdrawal_summary.minimum_amount, summary.currency)}</h2><small>{summary.withdrawal_summary.usd_bdt_rate ? `≈ ${formatMoney(Number(summary.withdrawal_summary.minimum_amount) * Number(summary.withdrawal_summary.usd_bdt_rate), "BDT")}` : "Waiting for admin exchange rate"}</small></article></Card>
            <Card className="dashboard-metric" asChild><article><p>Latest request</p><h2 className="withdrawal-latest-value">{summary.withdrawal_summary.last_request ? readableStatus(summary.withdrawal_summary.last_request.status) : "None"}</h2><small>{summary.withdrawal_summary.last_request ? new Date(summary.withdrawal_summary.last_request.created_at).toLocaleDateString() : "No prior payout request"}</small></article></Card>
          </section>}

          {!historyOnly && (
            <Card className={`panel withdrawal-form-panel${embedded ? " wallet-withdrawal-form" : ""}`} id={embedded ? "withdraw-request" : undefined}>
              <div className="panel-heading">
                <div><p className="eyebrow">SECURE REQUEST</p><h2>Request a withdrawal</h2><p className="panel-subtitle">Payout details are encrypted at rest. Only authorized withdrawal reviewers can view them.</p>{embedded && <p className="wallet-withdrawal-minimum">Minimum request: <strong>{formatMoney(summary.withdrawal_summary.minimum_amount, summary.currency)}</strong></p>}</div>
              </div>
              {!summary.withdrawal_summary.enabled ? (
                <div className="state withdrawal-disabled" role="status">Withdrawals are disabled until WorkBit configures its secure payout key and USD to BDT exchange rate.</div>
              ) : summary.withdrawal_summary.pending_request ? (
                <div className="state withdrawal-disabled" role="status">You have a {readableStatus(summary.withdrawal_summary.pending_request.status)} request. Wait for it to be resolved before submitting another.</div>
              ) : Number(summary.withdrawable_balance) < Number(summary.withdrawal_summary.minimum_amount) ? (
                <div className="state withdrawal-disabled" role="status">Your withdrawable earnings have not reached the configured minimum. Deposit balance can only be used for packages.</div>
              ) : (
                <form className="withdrawal-form" onSubmit={submitRequest} onInvalidCapture={(event) => showInvalidFieldToast(event.target)}>
                  <Label>
                    Wallet amount ({summary.currency})
                    <Input
                      name="amount"
                      type="number"
                      inputMode="decimal"
                      min={String(summary.withdrawal_summary.minimum_amount)}
                      max={String(summary.withdrawable_balance)}
                      step="0.00000001"
                      required
                      value={amount}
                      onChange={(event) => setAmount(event.target.value)}
                    />
                    <small>Withdrawable: {formatMoney(summary.withdrawable_balance, summary.currency)} · Minimum: {formatMoney(summary.withdrawal_summary.minimum_amount, summary.currency)}</small>
                  </Label>
                  <Label>Mobile banking service
                    <Select value={paymentMethod} onValueChange={(value) => setPaymentMethod(value as "BKASH" | "NAGAD")}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent><SelectItem value="BKASH">bKash</SelectItem><SelectItem value="NAGAD">Nagad</SelectItem></SelectContent>
                    </Select>
                  </Label>
                  <Label>
                    {paymentMethod} mobile number
                    <Input
                      name="destination"
                      type="tel"
                      inputMode="tel"
                      autoComplete="off"
                      minLength={11}
                      maxLength={16}
                      pattern="(\+?88)?01[3-9][0-9]{8}"
                      required
                      value={destination}
                      onChange={(event) => setDestination(event.target.value)}
                      placeholder="01XXXXXXXXX"
                    />
                    <small>Bangladesh number only. Encrypted and visible only to authorized payout reviewers.</small>
                  </Label>
                  {estimatedPayout !== null && <div className="withdrawal-payout-estimate"><span>Estimated mobile payout</span><strong>{formatMoney(estimatedPayout, "BDT")}</strong><small>Rate: 1 USD = {Number(summary.withdrawal_summary.usd_bdt_rate).toLocaleString()} BDT · fixed for this request</small></div>}
                  <Button className="primary" type="submit" disabled={!canWithdraw || submitting}>
                    {submitting ? "Submitting request…" : "Request bKash/Nagad payout"}
                  </Button>
                </form>
              )}
              {message && <Alert className={`inline-status${messageIsError ? " is-error" : ""}`} variant={messageIsError ? "destructive" : "default"} role={messageIsError ? "alert" : "status"}><AlertDescription>{message}</AlertDescription></Alert>}
            </Card>
          )}

          <Card className={`panel withdrawal-history-panel${embedded ? " wallet-withdrawal-history" : ""}`} id={embedded ? "withdrawal-history" : undefined}>
            <div className="panel-heading"><div><p className="eyebrow">REQUEST RECORDS</p><h2>{historyOnly || embedded ? "Withdrawal history" : "Recent requests"}</h2></div>{!historyOnly && !embedded && <Button className="text-link" variant="link" asChild><Link href="/withdrawals">View all →</Link></Button>}</div>
            {historyError ? <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{historyError}</AlertDescription></Alert> : <WithdrawalHistory records={historyOnly || embedded ? records : records.slice(0, 5)} currency={summary.currency} />}
          </Card>
        </>
      )}
    </>
  );
  if (embedded) return <div className="wallet-withdrawal-management">{content}</div>;
  return <Shell user={summary?.user}>{content}</Shell>;
}
