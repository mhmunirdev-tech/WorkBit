"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowRight, BadgeCheck, Clock3 } from "lucide-react";
import { api } from "../lib/api";
import { showToast } from "../lib/toast";
import { formatUsd } from "../lib/utils";
import { Shell } from "./shell";
import { Alert, AlertDescription } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Card } from "./ui/card";

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
  usd_bdt_rate: string | null;
  package_active: boolean;
  package_expires_at: string | null;
  latest_purchase: Purchase | null;
};

function formatBdt(amount: string) {
  return new Intl.NumberFormat("en-BD", {
    style: "currency",
    currency: "BDT",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(amount));
}

function PackagesContent() {
  const [catalog, setCatalog] = useState<PackageCatalog | null>(null);
  const [loading, setLoading] = useState(true);
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

  const latest = catalog?.latest_purchase;
  const pending = latest?.status === "PENDING";

  useEffect(() => {
    if (latest?.status === "REJECTED") {
      showToast({
        title: "Package payment not approved",
        description: latest.admin_note
          ? `Your last payment was not approved. ${latest.admin_note}`
          : "Your last payment was not approved. You can submit a new package payment.",
        variant: "destructive",
      });
    }
  }, [latest?.admin_note, latest?.status]);

  return (
    <main className="package-page package-catalog-page">
      <header className="package-page-header package-catalog-heading">
        <div>
          <p className="eyebrow">WORKBIT / EARNING</p>
          <h1>Choose your package</h1>
          <p>Select a plan that works for you. Pay by bKash or Nagad, and access starts after admin approval.</p>
        </div>
      </header>

      {error && <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}
      {loading ? <Card className="panel package-status-card" aria-busy="true"><p>Loading package options…</p></Card> : catalog && (
        <>
          {pending ? (
            <Card className="panel package-status-card">
              <Badge variant="outline"><Clock3 size={13} /> PAYMENT UNDER REVIEW</Badge>
              <h2>{latest.package_name} · {formatUsd(latest.amount)}</h2>
              <p>We received your {latest.payment_method} payment reference <strong>{latest.payment_reference}</strong>. Your package will activate after approval.</p>
              {latest.payment_amount_bdt && <p>Submitted payment amount: <strong>{formatBdt(latest.payment_amount_bdt)}</strong></p>}
            </Card>
          ) : (
            <>
              {catalog.package_active && (
                <Alert className="package-active-alert" role="status">
                  <AlertDescription>
                    <BadgeCheck size={17} /> Your package is active
                    {catalog.package_expires_at && <> until <strong>{new Date(catalog.package_expires_at).toLocaleDateString()}</strong></>}. You can select a package below to renew.
                  </AlertDescription>
                </Alert>
              )}
              {latest?.status === "REJECTED" && (
                <Alert className="state error-state" role="status">
                  <AlertDescription>Your last payment was not approved.{latest.admin_note ? ` ${latest.admin_note}` : ""} You can select a package and submit a new payment.</AlertDescription>
                </Alert>
              )}
              <section className="package-catalog" aria-label="Available earning packages">
                <div className="package-catalog-intro">
                  <div>
                    <h2>Available packages</h2>
                    <p>Every plan gives you full access to earning offers for its duration.</p>
                  </div>
                  <span>{catalog.packages.length} {catalog.packages.length === 1 ? "plan" : "plans"}</span>
                </div>
                <div className="package-plan-grid">
                  {catalog.packages.map((item) => (
                    <Link
                      className="package-plan-card"
                      href={`/deposit?package=${encodeURIComponent(item.code)}`}
                      key={item.code}
                      aria-label={`Choose ${item.name} package`}
                    >
                      <span className="package-plan-label">{item.duration_days >= 365 ? "BEST FOR LONG-TERM" : "GET STARTED"}</span>
                      <strong>{item.name}</strong>
                      <span className="package-plan-price">
                        <b>{formatUsd(item.amount)}</b>
                        <small>one-time</small>
                      </span>
                      {item.payment_amount_bdt && (
                        <span className="package-plan-payment">Pay {formatBdt(item.payment_amount_bdt)} via bKash or Nagad</span>
                      )}
                      <span className="package-plan-description">{item.description || "Full access to earning offers."}</span>
                      <span className="package-plan-duration"><Clock3 size={15} /> {item.duration_days} days of access</span>
                      <span className="package-plan-cta">Choose package <ArrowRight size={16} /></span>
                    </Link>
                  ))}
                </div>
              </section>
            </>
          )}
        </>
      )}
    </main>
  );
}

export function PackagesPage() {
  return <Shell><PackagesContent /></Shell>;
}
