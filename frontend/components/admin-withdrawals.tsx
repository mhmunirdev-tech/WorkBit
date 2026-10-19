"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import { showToast } from "../lib/toast";
import { formatUsd } from "../lib/utils";
import { Alert, AlertDescription } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";

type Withdrawal = {
  id: string;
  amount: string | number;
  currency: string;
  payout_amount: string | number | null;
  payout_currency: string | null;
  exchange_rate: string | number | null;
  method: string;
  destination_hint: string;
  status: string;
  payment_transaction_id: string | null;
  paid_at: string | null;
  created_at: string;
  updated_at: string;
};

type WithdrawalDetails = Withdrawal & {
  user_id: string;
  user_email: string;
  user_name: string;
  destination: string;
  admin_note: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
};

type PayoutSettings = {
  usd_bdt_rate: string | number | null;
  minimum_withdrawal_usd: string | number;
};

type Action = "approve" | "reject" | "complete";

function formatMoney(amount: string | number, currency: string) {
  return formatUsd(amount);
}

function formatSettingInput(value: string | number | null): string {
  if (value == null) return "";
  const normalized = String(value);
  if (!normalized.includes(".")) return normalized;
  const trimmed = normalized.replace(/0+$/, "").replace(/\.$/, "");
  return trimmed || "0";
}

export function AdminWithdrawals() {
  const [records, setRecords] = useState<Withdrawal[]>([]);
  const [payoutSettings, setPayoutSettings] = useState<PayoutSettings | null>(null);
  const [exchangeRate, setExchangeRate] = useState("");
  const [minimumWithdrawal, setMinimumWithdrawal] = useState("");
  const [selected, setSelected] = useState<WithdrawalDetails | null>(null);
  const [note, setNote] = useState("");
  const [transactionId, setTransactionId] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    setSelected(null);
    try {
      const [withdrawals, settings] = await Promise.all([
        api<Withdrawal[]>("/admin/withdrawals"),
        api<PayoutSettings>("/admin/payout-settings"),
      ]);
      setRecords(withdrawals);
      setPayoutSettings(settings);
      setExchangeRate(formatSettingInput(settings.usd_bdt_rate));
      setMinimumWithdrawal(formatSettingInput(settings.minimum_withdrawal_usd));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Withdrawal requests could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  async function saveExchangeRate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const updated = await api<PayoutSettings>("/admin/payout-settings", {
        method: "PUT",
        body: JSON.stringify({
          usd_bdt_rate: exchangeRate,
          minimum_withdrawal_usd: minimumWithdrawal,
        }),
      });
      setPayoutSettings(updated);
      setExchangeRate(formatSettingInput(updated.usd_bdt_rate));
      setMinimumWithdrawal(formatSettingInput(updated.minimum_withdrawal_usd));
      const updateMessage = "Payout settings updated. New requests will use the saved exchange rate and minimum.";
      setMessage(updateMessage);
      showToast({ title: "Payout settings updated", description: updateMessage, variant: "success" });
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "The payout exchange rate could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function viewDetails(withdrawal: Withdrawal) {
    setSelected(null);
    setTransactionId("");
    setNote("");
    setError("");
    setMessage("");
    setBusy(true);
    try {
      setSelected(await api<WithdrawalDetails>(`/admin/withdrawals/${withdrawal.id}`));
    } catch (detailError) {
      setError(detailError instanceof Error ? detailError.message : "Payout details could not be loaded.");
    } finally {
      setBusy(false);
    }
  }

  async function review(action: Action) {
    if (!selected) return;
    if (action === "complete" && !transactionId.trim()) return;
    if (action === "approve" && !window.confirm("Confirm the payout has already been sent to the user's destination. Approval will mark this withdrawal as paid.")) return;
    if (action === "complete" && !window.confirm("Confirm this payout has been sent to the user's destination and enter the transfer reference?")) return;

    setBusy(true);
    setError("");
    setMessage("");
    try {
      const updated = await api<Withdrawal>(`/admin/withdrawals/${selected.id}/${action}`, {
        method: "POST",
        body: JSON.stringify({
          note: note.trim() || null,
          ...(action === "complete" ? { transaction_id: transactionId.trim() } : {}),
        }),
      });
      setRecords((existing) => existing.map((item) => item.id === updated.id ? updated : item));
      setSelected((existing) => existing ? {
        ...existing,
        status: updated.status,
        payment_transaction_id: updated.payment_transaction_id,
        paid_at: updated.paid_at,
        updated_at: updated.updated_at,
      } : existing);
      setNote("");
      setTransactionId("");
      const reviewMessage = `Withdrawal marked ${updated.status.toLowerCase()}.`;
      setMessage(reviewMessage);
      showToast({ title: "Withdrawal reviewed", description: reviewMessage, variant: "success" });
    } catch (reviewError) {
      setError(reviewError instanceof Error ? reviewError.message : "The withdrawal could not be updated.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="admin-withdrawals-page">
      <header className="admin-withdrawals-header">
        <div>
          <p className="eyebrow">WORKBIT ADMIN</p>
          <h1>Manual withdrawals</h1>
          <p>Send the payout, then approve the request to mark it paid; rejected requests release the reserved balance.</p>
        </div>
        <div className="admin-withdrawals-links">
          <Button className="secondary-button" variant="outline" type="button" onClick={() => void refresh()} disabled={loading || busy}>Refresh</Button>
          <Button variant="link" asChild><Link href="/admin">Admin overview</Link></Button>
        </div>
      </header>

      {error && <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}
      {message && <Alert className="state" role="status"><AlertDescription>{message}</AlertDescription></Alert>}

      <Card className="panel admin-payout-settings">
        <div className="panel-heading">
          <div><p className="eyebrow">PAYOUT CONFIGURATION</p><h2>Exchange rate & withdrawal minimum</h2></div>
          <Badge variant="outline">{payoutSettings?.usd_bdt_rate ? "Configured" : "Required"}</Badge>
        </div>
        <p className="admin-payout-settings-copy">
          Both settings are stored in the database. Exchange-rate changes affect new requests only; the minimum amount is checked when a user requests a payout.
        </p>
        <form className="admin-payout-settings-form" onSubmit={(event) => void saveExchangeRate(event)}>
          <Label htmlFor="payout-usd-bdt-rate">1 USD equals (BDT)
            <Input
              id="payout-usd-bdt-rate"
              type="number"
              inputMode="decimal"
              min="0.0001"
              step="any"
              required
              value={exchangeRate}
              onChange={(event) => setExchangeRate(event.target.value)}
              placeholder="e.g. 120"
            />
          </Label>
          <Label htmlFor="payout-minimum-withdrawal">Minimum withdrawal (USD)
            <Input
              id="payout-minimum-withdrawal"
              type="number"
              inputMode="decimal"
              min="0.00000001"
              step="any"
              required
              value={minimumWithdrawal}
              onChange={(event) => setMinimumWithdrawal(event.target.value)}
              placeholder="e.g. 5.00"
            />
          </Label>
          <Button className="primary" type="submit" disabled={busy || !exchangeRate || Number(exchangeRate) <= 0 || !minimumWithdrawal || Number(minimumWithdrawal) <= 0}>
            {busy ? "Saving…" : "Save payout settings"}
          </Button>
        </form>
      </Card>

      <div className="admin-withdrawals-layout">
        <Card className="panel admin-withdrawals-list" aria-label="Withdrawal requests">
          <div className="panel-heading"><div><p className="eyebrow">REQUEST QUEUE</p><h2>All requests</h2></div></div>
          {loading ? <p className="state">Loading withdrawal requests…</p> : error && records.length === 0 ? (
            <p className="state" role="status">Withdrawal records are unavailable until the database request succeeds.</p>
          ) : records.length === 0 ? (
            <p className="state">There are no withdrawal requests to review.</p>
          ) : (
            <div className="admin-withdrawal-items">
              {records.map((record) => (
                <Button
                  variant="ghost"
                  className={`admin-withdrawal-item${selected?.id === record.id ? " is-selected" : ""}`}
                  type="button"
                  key={record.id}
                  onClick={() => void viewDetails(record)}
                  aria-pressed={selected?.id === record.id}
                >
                  <span><strong>{formatMoney(record.amount, record.currency)}{record.payout_amount != null && record.payout_currency ? ` → ${formatMoney(record.payout_amount, record.payout_currency)}` : ""}</strong><small>{record.method} · {record.destination_hint}</small></span>
                  <Badge className={`withdrawal-status withdrawal-${record.status.toLowerCase()}`} variant="outline">{record.status.toLowerCase()}</Badge>
                  <time dateTime={record.created_at}>{new Date(record.created_at).toLocaleDateString()}</time>
                </Button>
              ))}
            </div>
          )}
        </Card>

        <Card className="panel admin-withdrawal-detail" aria-label="Selected withdrawal">
          {!selected ? (
            <div className="dashboard-empty">
              <strong>{busy ? "Loading secure payout details…" : "Select a request"}</strong>
              <span>Full payout details are fetched only when a reviewer opens a request. Each read is audited.</span>
            </div>
          ) : (
            <>
              <div className="panel-heading">
                <div><p className="eyebrow">REQUEST DETAILS</p><h2>{formatMoney(selected.amount, selected.currency)}</h2></div>
                <Badge className={`withdrawal-status withdrawal-${selected.status.toLowerCase()}`} variant="outline">{selected.status.toLowerCase()}</Badge>
              </div>
              <dl className="admin-withdrawal-fields">
                <div><dt>User</dt><dd>{selected.user_name} · {selected.user_email}</dd></div>
                <div><dt>Mobile banking</dt><dd>{selected.method}</dd></div>
                <div><dt>Destination</dt><dd className="admin-destination">{selected.destination}</dd></div>
                {selected.payout_amount != null && selected.payout_currency && <div><dt>Expected payout</dt><dd>{formatMoney(selected.payout_amount, selected.payout_currency)}{selected.exchange_rate != null ? ` · 1 ${selected.currency} = ${selected.exchange_rate} BDT` : ""}</dd></div>}
                <div><dt>Submitted</dt><dd><time dateTime={selected.created_at}>{new Date(selected.created_at).toLocaleString()}</time></dd></div>
                {selected.payment_transaction_id && <div><dt>Payment transaction ID</dt><dd>{selected.payment_transaction_id}</dd></div>}
                {selected.paid_at && <div><dt>Paid at</dt><dd><time dateTime={selected.paid_at}>{new Date(selected.paid_at).toLocaleString()}</time></dd></div>}
                {selected.admin_note && <div><dt>Previous review note</dt><dd>{selected.admin_note}</dd></div>}
              </dl>

              {(selected.status === "PENDING" || selected.status === "PROCESSING") && (
                <div className="admin-withdrawal-review">
                  {selected.status === "PROCESSING" && (
                    <>
                      <label htmlFor="withdrawal-payment-transaction-id">Payment transaction ID (required to mark as paid)</label>
                      <Input
                        id="withdrawal-payment-transaction-id"
                        maxLength={128}
                        required
                        value={transactionId}
                        onChange={(event) => setTransactionId(event.target.value)}
                      />
                    </>
                  )}
                  <label htmlFor="withdrawal-review-note">Review note (optional)</label>
                  <Textarea id="withdrawal-review-note" maxLength={500} value={note} onChange={(event) => setNote(event.target.value)} />
                  <div className="admin-withdrawal-actions">
                    {selected.status === "PENDING" && <Button className="primary" type="button" disabled={busy} onClick={() => void review("approve")}>Approve</Button>}
                    {selected.status === "PROCESSING" && <Button className="primary" type="button" disabled={busy || !transactionId.trim()} onClick={() => void review("complete")}>Mark as paid</Button>}
                    <Button className="secondary-button is-danger" variant="destructive" type="button" disabled={busy} onClick={() => void review("reject")}>Reject and release funds</Button>
                  </div>
                </div>
              )}
            </>
          )}
        </Card>
      </div>
    </main>
  );
}
