"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ArrowLeft, ArrowDownToLine, Clock3 } from "lucide-react";
import { api } from "../lib/api";
import { showInvalidFieldToast, showToast } from "../lib/toast";
import { formatUsd } from "../lib/utils";
import { Shell } from "./shell";
import { Alert, AlertDescription } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";

type PackageOption = {
  code: string;
  name: string;
  description: string;
  amount: string;
  currency: string;
  payment_amount_bdt: string | null;
  duration_days: number;
};

type Purchase = {
  package_name: string;
  amount: string;
  currency: string;
  payment_amount_bdt: string | null;
  payment_method: "BKASH" | "NAGAD";
  payment_reference: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  admin_note: string | null;
};

type PackageCatalog = {
  packages: PackageOption[];
  payment_instructions: Record<"BKASH" | "NAGAD", string>;
  usd_bdt_rate: string | null;
  latest_purchase: Purchase | null;
};

function formatBdt(amount: number) {
  return new Intl.NumberFormat("en-BD", {
    style: "currency",
    currency: "BDT",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function DepositPage({ packageCode }: { packageCode: string }) {
  const [catalog, setCatalog] = useState<PackageCatalog | null>(null);
  const [paymentMethod, setPaymentMethod] = useState<"BKASH" | "NAGAD">("BKASH");
  const [reference, setReference] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setError("");
    try {
      setCatalog(await api<PackageCatalog>("/packages"));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Package information could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function submitPayment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const selectedPackage = catalog?.packages.find((item) => item.code === packageCode);
    if (!selectedPackage) return;

    setBusy(true);
    setError("");
    try {
      const purchase = await api<Purchase>("/package-purchases", {
        method: "POST",
        body: JSON.stringify({
          package_code: selectedPackage.code,
          payment_method: paymentMethod,
          payment_reference: reference.trim(),
        }),
      });
      setCatalog((current) => current ? { ...current, latest_purchase: purchase } : current);
      setReference("");
      showToast({
        title: "Deposit request submitted",
        description: "Your package payment is now pending admin review.",
        variant: "success",
      });
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "Package payment could not be submitted.";
      setError(message);
      showToast({
        title: "Deposit request failed",
        description: message,
        variant: "destructive",
      });
    } finally {
      setBusy(false);
    }
  }

  const selectedPackage = catalog?.packages.find((item) => item.code === packageCode);
  const rate = catalog?.usd_bdt_rate ? Number(catalog.usd_bdt_rate) : null;
  const amountBdt = selectedPackage?.payment_amount_bdt
    ? Number(selectedPackage.payment_amount_bdt)
    : null;
  const destination = catalog?.payment_instructions[paymentMethod]?.trim();
  const pending = catalog?.latest_purchase?.status === "PENDING";

  useEffect(() => {
    if (!loading && catalog && (!rate || rate <= 0)) {
      showToast({
        title: "Deposit temporarily unavailable",
        description: "Package payment is unavailable until the USD to BDT exchange rate is configured.",
        variant: "destructive",
      });
    }
  }, [catalog, loading, rate]);

  return (
    <Shell>
      <main className="package-page">
        <Button variant="link" asChild><Link href="/packages"><ArrowLeft size={15} /> Back to packages</Link></Button>
        <header className="package-page-header">
          <span className="package-page-icon"><ArrowDownToLine size={22} /></span>
          <p className="eyebrow">PACKAGE PAYMENT · STEP 2 OF 2</p>
          <h1>Complete your package payment</h1>
          <p>Send the exact amount shown below, then enter the transaction reference for admin review.</p>
        </header>

        {error && <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}
        {loading ? <Card className="panel package-status-card" aria-busy="true"><p>Loading payment details…</p></Card> : !catalog ? null : !selectedPackage ? (
          <Card className="panel package-status-card">
            <h2>This package is no longer available</h2>
            <p>Please choose an available package to continue.</p>
            <Button className="primary" asChild><Link href="/packages">Choose a package</Link></Button>
          </Card>
        ) : pending ? (
          <Card className="panel package-status-card">
            <Badge variant="outline"><Clock3 size={13} /> PAYMENT UNDER REVIEW</Badge>
            <h2>{catalog.latest_purchase?.package_name} · {formatUsd(catalog.latest_purchase?.amount ?? "0")}</h2>
            <p>Reference <strong>{catalog.latest_purchase?.payment_reference}</strong> via {catalog.latest_purchase?.payment_method} is being reviewed. You can submit another package payment after this review is complete.</p>
            <Button variant="outline" asChild><Link href="/packages">Back to packages</Link></Button>
          </Card>
        ) : !rate || rate <= 0 ? (
          <Alert className="state error-state" variant="destructive">
            <AlertDescription>Package payment is temporarily unavailable until WorkBit configures the USD to BDT exchange rate.</AlertDescription>
          </Alert>
        ) : (
          <Card className="panel package-payment-card">
            <div className="package-payment-heading">
              <div><p className="eyebrow">SELECTED PACKAGE</p><h2>{selectedPackage.name}</h2></div>
              <Badge variant="outline">{selectedPackage.duration_days} days</Badge>
            </div>
            <div className="package-payment-summary">
              <p>Package price <strong>{formatUsd(selectedPackage.amount)}</strong></p>
              <p>Send exactly <strong>{formatBdt(amountBdt ?? 0)}</strong></p>
              <small>Calculated at 1 USD = BDT {rate.toLocaleString("en-BD")} and fixed when you submit the payment.</small>
            </div>

            <form className="package-payment-form" onSubmit={(event) => void submitPayment(event)} onInvalidCapture={(event) => showInvalidFieldToast(event.target)}>
              <Label>Payment method
                <Select value={paymentMethod} onValueChange={(value) => setPaymentMethod(value as "BKASH" | "NAGAD")}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="BKASH">bKash</SelectItem>
                    <SelectItem value="NAGAD">Nagad</SelectItem>
                  </SelectContent>
                </Select>
              </Label>
              <div className={`package-payment-destination is-${paymentMethod.toLowerCase()}`}>
                <span>Send {formatBdt(amountBdt ?? 0)} via {paymentMethod === "BKASH" ? "bKash" : "Nagad"} to</span>
                <strong>{destination || "Payment account is not configured"}</strong>
              </div>
              <Label htmlFor="package-payment-reference">Transaction reference
                <Input
                  id="package-payment-reference"
                  value={reference}
                  onChange={(event) => setReference(event.target.value)}
                  minLength={5}
                  maxLength={120}
                  required
                  placeholder="Enter your bKash/Nagad transaction ID"
                />
              </Label>
              <Button className="primary" type="submit" disabled={busy || !destination}>
                {busy ? "Submitting…" : "Submit payment for review"}
              </Button>
            </form>
          </Card>
        )}
      </main>
    </Shell>
  );
}
