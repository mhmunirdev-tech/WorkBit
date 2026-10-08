"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ArrowUpRight, BadgeCheck, Camera, Copy, WalletCards } from "lucide-react";
import { api } from "../lib/api";
import { Shell, ShellUser } from "./shell";
import { Alert, AlertDescription } from "./ui/alert";
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Skeleton } from "./ui/skeleton";

type AccountData = {
  currency: string;
  user: ShellUser & {
    country: string;
    created_at: string;
    referral_code: string;
    referral_url: string;
    avatar_url: string | null;
  };
  available_balance: string | number;
  pending_balance: string | number;
  lifetime_earned: string | number;
  lifetime_withdrawn: string | number;
  stats: {
    referrals: number;
    active_referrals: number;
    referral_earnings: string | number;
    pending_referral_earnings: string | number;
  };
  withdrawal_summary: {
    enabled: boolean;
    minimum_amount: string | number;
  };
};

function useAccount() {
  const [account, setAccount] = useState<AccountData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api<AccountData>("/dashboard")
      .then((result) => {
        if (active) setAccount(result);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Account information could not be loaded.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return { account, setAccount, loading, error };
}

function AccountState({ loading, error }: { loading: boolean; error: string }) {
  if (loading) {
    return (
      <Card className="panel" aria-busy="true" aria-label="Loading account information">
        <Skeleton className="h-5 w-1/2" />
        <Skeleton className="h-4 w-1/3" />
      </Card>
    );
  }
  if (error) return <Alert className="state error-state" variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>;
  return null;
}

function formatMoney(value: string | number, currency: string) {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(Number(value));
}

export function ProfilePage() {
  const { account, setAccount, loading, error } = useAccount();
  const photoInput = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [photoMessage, setPhotoMessage] = useState("");
  const [referralMessage, setReferralMessage] = useState("");

  async function uploadPhoto(file: File | undefined) {
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setPhotoMessage("JPEG, PNG, or WebP images are supported.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setPhotoMessage("Choose an image that is 5 MB or smaller.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    setUploading(true);
    setPhotoMessage("");
    try {
      const result = await api<{ avatar_url: string }>("/profile/avatar", {
        method: "POST",
        body: formData,
      });
      setAccount((current) => current
        ? { ...current, user: { ...current.user, avatar_url: result.avatar_url } }
        : current);
      setPhotoMessage("Profile photo updated.");
    } catch (reason) {
      setPhotoMessage(reason instanceof Error ? reason.message : "Profile photo could not be uploaded.");
    } finally {
      setUploading(false);
      if (photoInput.current) photoInput.current.value = "";
    }
  }

  async function copyReferralLink() {
    if (!account) return;
    try {
      await navigator.clipboard.writeText(account.user.referral_url);
      setReferralMessage("Referral link copied.");
    } catch {
      setReferralMessage("Could not copy the referral link. Select and copy it manually.");
    }
  }

  return (
    <Shell user={account?.user}>
      <header className="top">
        <div>
          <p className="eyebrow">MY ACCOUNT</p>
          <h1>Profile & earnings</h1>
          <p className="muted">Your account details, wallet snapshot, and referral activity in one place.</p>
        </div>
      </header>
      <AccountState loading={loading} error={error} />
      {account && (
        <div className="profile-page">
          <Card className="panel profile-hero-card">
            <div className="profile-hero-identity">
              <div className="profile-photo-wrap">
                <Avatar className="profile-photo" aria-hidden="true">
                  {account.user.avatar_url && <AvatarImage src={account.user.avatar_url} alt="" />}
                  <AvatarFallback>{account.user.full_name.slice(0, 1).toUpperCase()}</AvatarFallback>
                </Avatar>
                <Button
                  className="profile-photo-button"
                  type="button"
                  variant="secondary"
                  size="icon"
                  aria-label="Upload profile photo"
                  disabled={uploading}
                  onClick={() => photoInput.current?.click()}
                >
                  <Camera size={16} aria-hidden="true" />
                </Button>
                <input
                  ref={photoInput}
                  className="sr-only"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  aria-label="Choose profile photo"
                  onChange={(event) => void uploadPhoto(event.target.files?.[0])}
                />
              </div>
              <div className="profile-hero-copy">
                <span className="profile-member-label"><BadgeCheck size={14} /> WORKBIT MEMBER</span>
                <h2>{account.user.full_name}</h2>
                <p>{account.user.email}</p>
                <div className="profile-hero-badges">
                  <Badge className="profile-status-badge" variant="outline">{account.user.status.replaceAll("_", " ")}</Badge>
                  <Badge className={`profile-status-badge ${account.user.email_verified ? "is-verified" : "is-unverified"}`} variant="outline">
                    {account.user.email_verified ? "Email verified" : "Email not verified"}
                  </Badge>
                </div>
              </div>
              <Button className="profile-settings-link" variant="outline" asChild>
                <Link href="/settings">Account settings <ArrowUpRight size={15} /></Link>
              </Button>
            </div>
            <div className="profile-hero-footer">
              <span>Member since <strong>{new Date(account.user.created_at).toLocaleDateString()}</strong></span>
              <span>Country <strong>{account.user.country}</strong></span>
              {photoMessage && <span className="profile-photo-message" role="status">{photoMessage}</span>}
              {uploading && <span className="profile-photo-message" role="status">Uploading photo…</span>}
            </div>
          </Card>

          <section className="profile-balance-grid" aria-label="Wallet summary">
            <Card className="profile-balance-card is-primary">
              <span className="profile-balance-icon"><WalletCards size={17} /></span>
              <p>Available balance</p>
              <strong>{formatMoney(account.available_balance, account.currency)}</strong>
              <small>Ready to withdraw</small>
            </Card>
            <Card className="profile-balance-card">
              <span className="profile-balance-icon is-green"><ArrowUpRight size={17} /></span>
              <p>Total earnings</p>
              <strong>{formatMoney(account.lifetime_earned, account.currency)}</strong>
              <small>Recorded on your wallet ledger</small>
            </Card>
            <Card className="profile-balance-card">
              <span className="profile-balance-icon is-amber"><WalletCards size={17} /></span>
              <p>Total withdrawn</p>
              <strong>{formatMoney(account.lifetime_withdrawn, account.currency)}</strong>
              <small>Completed withdrawals</small>
            </Card>
            <Card className="profile-balance-card">
              <span className="profile-balance-icon is-violet"><WalletCards size={17} /></span>
              <p>Pending balance</p>
              <strong>{formatMoney(account.pending_balance, account.currency)}</strong>
              <small>Awaiting validation</small>
            </Card>
          </section>

          <section className="profile-details-grid">
            <Card className="panel profile-detail-card">
              <div className="profile-section-heading">
                <div><p className="eyebrow">INVITE & EARN</p><h2>Your referral program</h2></div>
                <Link href="/referrals">View referrals <ArrowUpRight size={14} /></Link>
              </div>
              <p className="profile-section-copy">Share your personal invite link and follow the referral activity linked to your account.</p>
              <label className="profile-field-label" htmlFor="profile-referral-link">Your referral link</label>
              <div className="profile-referral-link">
                <input id="profile-referral-link" readOnly value={account.user.referral_url} onFocus={(event) => event.currentTarget.select()} />
                <Button className="secondary-button" variant="outline" type="button" onClick={() => void copyReferralLink()}>
                  <Copy size={14} /> Copy
                </Button>
              </div>
              {referralMessage && <p className="profile-feedback" role="status">{referralMessage}</p>}
              <div className="profile-referral-stats">
                <div><strong>{account.stats.referrals}</strong><span>Total referrals</span></div>
                <div><strong>{account.stats.active_referrals}</strong><span>Active users</span></div>
                <div><strong>{formatMoney(account.stats.referral_earnings, account.currency)}</strong><span>Referral earnings</span></div>
              </div>
              <p className="profile-pending-referral">Pending referral earnings <strong>{formatMoney(account.stats.pending_referral_earnings, account.currency)}</strong></p>
            </Card>

            <Card className="panel profile-package-card">
              <span className="profile-package-icon"><WalletCards size={19} /></span>
              <p className="eyebrow">DEPOSIT PACKAGES</p>
              <h2>Packages are not available yet</h2>
              <p>WorkBit has not enabled a payment provider or deposit packages. No package purchase or deposit can be made right now.</p>
              <span className="profile-coming-soon">NOT AVAILABLE</span>
            </Card>
          </section>

          <Card className="panel profile-account-card">
            <div className="profile-section-heading">
              <div><p className="eyebrow">ACCOUNT DETAILS</p><h2>Your information</h2></div>
            </div>
            <dl className="account-details">
              <div><dt>Account status</dt><dd>{account.user.status.replaceAll("_", " ")}</dd></div>
              <div><dt>Email address</dt><dd className="profile-email-value">{account.user.email}</dd></div>
              <div><dt>Country</dt><dd>{account.user.country}</dd></div>
              <div><dt>Referral code</dt><dd>{account.user.referral_code}</dd></div>
              <div><dt>Minimum withdrawal</dt><dd>{account.withdrawal_summary.enabled ? formatMoney(account.withdrawal_summary.minimum_amount, account.currency) : "Currently unavailable"}</dd></div>
            </dl>
          </Card>
        </div>
      )}
    </Shell>
  );
}

export function SettingsPage() {
  const { account, loading, error } = useAccount();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function resendVerification() {
    setBusy(true);
    setMessage("");
    try {
      const result = await api<{ message: string }>("/auth/resend-verification", { method: "POST" });
      setMessage(result.message);
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "The verification request could not be sent.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell user={account?.user}>
      <header className="top">
        <div>
          <p className="eyebrow">PREFERENCES & SECURITY</p>
          <h1>Account settings</h1>
          <p className="muted">Manage the security actions currently supported for your account.</p>
        </div>
      </header>
      <AccountState loading={loading} error={error} />
      {account && (
        <Card className="panel settings-card">
          <div className="panel-heading">
            <div>
              <h2>Email verification</h2>
              <p className="panel-subtitle">A verified email helps protect access to your WorkBit account.</p>
            </div>
            <Badge className={`settings-status ${account.user.email_verified ? "is-good" : "needs-action"}`} variant="outline">
              {account.user.email_verified ? "Verified" : "Not verified"}
            </Badge>
          </div>
          <p className="settings-email">{account.user.email}</p>
          {!account.user.email_verified && (
            <Button className="primary" type="button" onClick={resendVerification} disabled={busy}>
              {busy ? "Requesting…" : "Resend verification email"}
            </Button>
          )}
          {message && <Alert className="inline-status" role="status"><AlertDescription>{message}</AlertDescription></Alert>}
          <div className="settings-divider" />
          <h2>Password</h2>
          <p className="panel-subtitle">Password recovery is available through the secure reset flow.</p>
          <Button className="text-link" variant="link" asChild><Link href="/forgot-password">Reset your password →</Link></Button>
          <p className="muted settings-limitation">Other preferences and session management are not exposed by the current account API.</p>
        </Card>
      )}
    </Shell>
  );
}
