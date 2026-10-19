"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { Banknote, Plus, Smartphone, X } from "lucide-react";
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

type PayoutAccount = {
  id: string;
  method: "BKASH" | "NAGAD";
  destination_hint: string;
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
  const [payoutAccounts, setPayoutAccounts] = useState<PayoutAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [summaryError, setSummaryError] = useState("");
  const [historyError, setHistoryError] = useState("");
  const [payoutAccountsError, setPayoutAccountsError] = useState("");
  const active = useRef(false);

  const refresh = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true);
    const [summaryResult, historyResult, payoutAccountsResult] = await Promise.allSettled([
      api<Summary>("/dashboard"),
      api<WithdrawalRecord[]>("/withdrawals"),
      api<PayoutAccount[]>("/wallet/payout-accounts"),
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
    if (payoutAccountsResult.status === "fulfilled") {
      setPayoutAccounts(payoutAccountsResult.value);
      setPayoutAccountsError("");
    } else {
      setPayoutAccounts([]);
      setPayoutAccountsError(payoutAccountsResult.reason instanceof Error ? payoutAccountsResult.reason.message : "Saved payout accounts could not be loaded.");
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
    payoutAccounts,
    setPayoutAccounts,
    loading,
    refresh,
    summaryError,
    historyError,
    setHistoryError,
    payoutAccountsError,
  };
}

function PayoutAccountsPanel({
  accounts,
  error,
  setAccounts,
}: {
  accounts: PayoutAccount[];
  error: string;
  setAccounts: React.Dispatch<React.SetStateAction<PayoutAccount[]>>;
}) {
  const [method, setMethod] = useState<PayoutAccount["method"]>("BKASH");
  const [number, setNumber] = useState("");
  const [code, setCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [editingAccountId, setEditingAccountId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [messageIsError, setMessageIsError] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (dialogOpen && !dialog.open) dialog.showModal();
    if (!dialogOpen && dialog.open) dialog.close();
  }, [dialogOpen]);

  async function saveAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    setMessageIsError(false);
    try {
      const accountContext = {
        method,
        destination: number,
        ...(editingAccountId ? { account_id: editingAccountId } : {}),
      };
      if (!codeSent) {
        const result = await api<{ message: string }>("/wallet/payout-accounts/otp", {
          method: "POST",
          body: JSON.stringify(accountContext),
        });
        setCodeSent(true);
        setMessage(result.message);
        return;
      }
      const saved = await api<PayoutAccount>("/wallet/payout-accounts", {
        method: "POST",
        body: JSON.stringify({ ...accountContext, code }),
      });
      setAccounts((current) => {
        const updated = editingAccountId
          ? current.map((account) => account.id === editingAccountId ? saved : account)
          : [...current, saved];
        return updated.sort((a, b) => a.method.localeCompare(b.method));
      });
      setNumber("");
      setCode("");
      setCodeSent(false);
      setEditingAccountId(null);
      setMessage(`${method === "BKASH" ? "bKash" : "Nagad"} number verified and ${editingAccountId ? "updated" : "saved"} securely.`);
    } catch (saveError) {
      setMessage(saveError instanceof Error ? saveError.message : "The payout number could not be saved.");
      setMessageIsError(true);
    } finally {
      setSaving(false);
    }
  }

  async function removeAccount(account: PayoutAccount) {
    setSaving(true);
    setMessage("");
    setMessageIsError(false);
    try {
      await api<void>(`/wallet/payout-accounts/${account.id}`, { method: "DELETE" });
      setAccounts((current) => current.filter((item) => item.id !== account.id));
      setMessage(`${account.method === "BKASH" ? "bKash" : "Nagad"} number removed.`);
    } catch (removeError) {
      setMessage(removeError instanceof Error ? removeError.message : "The payout number could not be removed.");
      setMessageIsError(true);
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <Card className="panel wallet-payout-accounts" id="payout-accounts">
        <div className="panel-heading payout-accounts-heading">
          <div><p className="eyebrow">SAVED PAYOUT ACCOUNTS</p><h2>Withdrawal accounts</h2><p className="panel-subtitle">Choose where WorkBit should send your manually reviewed withdrawal.</p></div>
          <Button type="button" className="payout-add-button" onClick={() => { setMessage(""); setNumber(""); setCode(""); setCodeSent(false); setEditingAccountId(null); setMethod("BKASH"); setDialogOpen(true); }}>
            <Plus size={17} aria-hidden="true" /> Add Account
          </Button>
        </div>
        {error && <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}
        {accounts.length ? (
          <div className="payout-account-grid">
            {accounts.map((account) => {
              const displayName = account.method === "BKASH" ? "bKash" : "Nagad";
              return (
                <article className={`payout-account-card payout-account-${account.method.toLowerCase()}`} key={account.id}>
                  <span className="payout-account-icon" aria-hidden="true"><Smartphone size={19} /></span>
                  <div className="payout-account-info">
                    <strong>{displayName}</strong>
                    <span>{account.destination_hint}</span>
                    <small>Saved for manual withdrawals</small>
                  </div>
                  <Button type="button" variant="ghost" disabled={saving} onClick={() => { setMessage(""); setEditingAccountId(account.id); setMethod(account.method); setNumber(""); setCode(""); setCodeSent(false); setDialogOpen(true); }}>Replace</Button>
                  <span className="payout-account-ready"><Banknote size={14} aria-hidden="true" /> Ready</span>
                  <Button type="button" variant="ghost" aria-label={`Remove ${displayName} ${account.destination_hint}`} disabled={saving} onClick={() => void removeAccount(account)}>Remove</Button>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="payout-accounts-empty">
            <span className="payout-account-icon" aria-hidden="true"><Smartphone size={19} /></span>
            <div><strong>No payout accounts yet</strong><small>Add your bKash or Nagad number to receive withdrawals.</small></div>
          </div>
        )}
        {message && <Alert className={`inline-status${messageIsError ? " is-error" : ""}`} variant={messageIsError ? "destructive" : "default"} role={messageIsError ? "alert" : "status"}><AlertDescription>{message}</AlertDescription></Alert>}
      </Card>
      <dialog
        ref={dialogRef}
        className="payout-account-dialog"
        aria-labelledby="payout-dialog-title"
        onCancel={(event) => { event.preventDefault(); setDialogOpen(false); }}
        onClose={() => setDialogOpen(false)}
        onClick={(event) => { if (event.target === event.currentTarget) setDialogOpen(false); }}
      >
        <div className="payout-dialog-heading">
          <div><p className="eyebrow">WALLET SETTINGS</p><h2 id="payout-dialog-title">{editingAccountId ? "Replace payout account" : "Add payout account"}</h2><p>A code will be sent to your registered email before your number is saved.</p></div>
          <Button type="button" variant="ghost" className="payout-dialog-close" aria-label="Close dialog" onClick={() => setDialogOpen(false)}><X size={19} /></Button>
        </div>
        <div className="payout-dialog-forms">
          <form className={`payout-account-form payout-dialog-form payout-account-${method.toLowerCase()}`} onSubmit={(event) => void saveAccount(event)} onInvalidCapture={(event) => showInvalidFieldToast(event.target)}>
            <Label>Service
              <Select value={method} disabled={Boolean(editingAccountId)} onValueChange={(value) => { setMethod(value as PayoutAccount["method"]); setCodeSent(false); setCode(""); }}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="BKASH" disabled={accounts.filter((account) => account.method === "BKASH").length >= 2}>bKash ({accounts.filter((account) => account.method === "BKASH").length}/2)</SelectItem>
                  <SelectItem value="NAGAD" disabled={accounts.filter((account) => account.method === "NAGAD").length >= 2}>Nagad ({accounts.filter((account) => account.method === "NAGAD").length}/2)</SelectItem>
                </SelectContent>
              </Select>
            </Label>
            <Label htmlFor="payout-number">{method === "BKASH" ? "bKash number" : "Nagad number"}</Label>
            <Input
              id="payout-number"
              name="payout-number"
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              minLength={11}
              maxLength={16}
              pattern="(\+?88)?01[3-9][0-9]{8}"
              placeholder="01XXXXXXXXX"
              value={number}
              onChange={(event) => { setNumber(event.target.value); setCodeSent(false); setCode(""); }}
              required
              aria-describedby="payout-number-help"
            />
            <small id="payout-number-help">You can save up to two numbers for each service.</small>
            {codeSent && <Label htmlFor="payout-account-code">Email confirmation code
              <Input id="payout-account-code" name="code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={code} onChange={(event) => setCode(event.target.value)} required />
            </Label>}
            <div className="payout-account-actions">
              <Button type="submit" disabled={saving || !number.trim() || (codeSent && code.length !== 6)}>
                {saving ? "Please wait…" : codeSent ? `Verify and ${editingAccountId ? "replace" : "save"} number` : "Send email code"}
              </Button>
            </div>
          </form>
        </div>
        {message && <Alert className={`inline-status${messageIsError ? " is-error" : ""}`} variant={messageIsError ? "destructive" : "default"} role={messageIsError ? "alert" : "status"}><AlertDescription>{message}</AlertDescription></Alert>}
      </dialog>
    </>
  );
}

function WithdrawalHistory({ records, currency }: { records: WithdrawalRecord[]; currency: string }) {
  if (records.length === 0) {
    return (
      <div className="dashboard-empty">
        <strong>No withdrawal requests</strong>
        <span>When you submit a request, its review status will appear here.</span>
        <Link href="/withdraw">Go to withdrawal page</Link>
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
    payoutAccounts,
    setPayoutAccounts,
    loading,
    refresh,
    summaryError,
    historyError,
    payoutAccountsError,
  } = useWithdrawalData();
  const [amount, setAmount] = useState("");
  const [accountId, setAccountId] = useState("");
  const [code, setCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [sendingCode, setSendingCode] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [messageIsError, setMessageIsError] = useState(false);
  const selectedAccount = payoutAccounts.find((account) => account.id === accountId);
  const paymentMethod = selectedAccount?.method ?? "BKASH";
  const hasSelectedAccount = selectedAccount !== undefined;
  useEffect(() => {
    if (!payoutAccounts.some((account) => account.id === accountId) && payoutAccounts.length > 0) {
      setAccountId(payoutAccounts[0].id);
    }
  }, [accountId, payoutAccounts]);
  const canWithdraw = Boolean(
    summary?.withdrawal_summary.enabled &&
    !summary.withdrawal_summary.pending_request &&
    hasSelectedAccount &&
    Number(summary.withdrawable_balance) >= Number(summary.withdrawal_summary.minimum_amount) &&
    Number(amount) >= Number(summary.withdrawal_summary.minimum_amount) &&
    Number(amount) <= Number(summary.withdrawable_balance)
  );
  const estimatedPayout = summary?.withdrawal_summary.usd_bdt_rate && amount
    ? Number(amount) * Number(summary.withdrawal_summary.usd_bdt_rate)
    : null;

  async function submitRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setMessage("");
    setMessageIsError(false);
    try {
      const request = await api<WithdrawalRecord>("/withdrawals", {
        method: "POST",
        body: JSON.stringify({ amount, account_id: accountId, payment_method: paymentMethod, code }),
      });
      setRecords((existing) => [request, ...existing]);
      setAmount("");
      setCode("");
      setCodeSent(false);
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

  async function sendWithdrawalCode() {
    if (!selectedAccount) return;
    setSendingCode(true);
    setMessage("");
    setMessageIsError(false);
    try {
      const result = await api<{ message: string }>("/withdrawals/otp", {
        method: "POST",
        body: JSON.stringify({ amount, account_id: selectedAccount.id }),
      });
      setCodeSent(true);
      setMessage(result.message);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "The confirmation code could not be sent.");
      setMessageIsError(true);
    } finally {
      setSendingCode(false);
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

          {embedded && (
            <PayoutAccountsPanel accounts={payoutAccounts} error={payoutAccountsError} setAccounts={setPayoutAccounts} />
          )}

          {embedded && (
            <Card className="panel wallet-withdrawal-link">
              <div><p className="eyebrow">READY TO WITHDRAW?</p><h2>Withdraw your earnings</h2><p className="panel-subtitle">Create a withdrawal request on the dedicated page. Your request will be reviewed manually.</p></div>
              <Button className="primary" asChild><Link href="/withdraw">Go to Withdraw <span aria-hidden="true">→</span></Link></Button>
            </Card>
          )}

          {!historyOnly && !embedded && (
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
                      onChange={(event) => { setAmount(event.target.value); setCodeSent(false); setCode(""); }}
                    />
                    <small>Withdrawable: {formatMoney(summary.withdrawable_balance, summary.currency)} · Minimum: {formatMoney(summary.withdrawal_summary.minimum_amount, summary.currency)}</small>
                  </Label>
                  <Label>Pay out to
                    <Select value={accountId} onValueChange={(value) => { setAccountId(value); setCodeSent(false); setCode(""); }}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {payoutAccounts.map((account) => (
                          <SelectItem key={account.id} value={account.id}>
                            {account.method === "BKASH" ? "bKash" : "Nagad"} · {account.destination_hint}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </Label>
                  {!hasSelectedAccount && <div className="state withdrawal-disabled" role="status">Save a {paymentMethod === "BKASH" ? "bKash" : "Nagad"} number in your wallet before requesting a withdrawal. <Link href="/wallet#payout-accounts">Manage payout accounts</Link></div>}
                  {estimatedPayout !== null && <div className="withdrawal-payout-estimate"><span>Estimated mobile payout</span><strong>{formatMoney(estimatedPayout, "BDT")}</strong><small>Rate: 1 USD = {Number(summary.withdrawal_summary.usd_bdt_rate).toLocaleString()} BDT · fixed for this request</small></div>}
                  {!codeSent ? (
                    <Button className="primary" type="button" disabled={!canWithdraw || sendingCode} onClick={() => void sendWithdrawalCode()}>
                      {sendingCode ? "Sending email code…" : "Send withdrawal confirmation code"}
                    </Button>
                  ) : (
                    <>
                      <Label htmlFor="withdrawal-email-code">Confirmation code sent to {summary.user.email}
                        <Input id="withdrawal-email-code" name="code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={code} onChange={(event) => setCode(event.target.value)} required />
                      </Label>
                      <Button className="primary" type="submit" disabled={!canWithdraw || submitting || code.length !== 6}>
                        {submitting ? "Submitting request…" : "Verify code and request withdrawal"}
                      </Button>
                    </>
                  )}
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
