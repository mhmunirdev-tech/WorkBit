"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowUpRight, BadgeCheck, Camera, Copy, KeyRound, Save, UserRound, WalletCards } from "lucide-react";
import { api } from "../lib/api";
import { useLiveRefresh } from "../lib/use-live-refresh";
import { formatUsd } from "../lib/utils";
import { Shell, ShellUser, WALLET_UPDATED_EVENT } from "./shell";
import { Alert, AlertDescription } from "./ui/alert";
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { PasswordInput } from "./ui/password-input";
import { Skeleton } from "./ui/skeleton";
import { showToast } from "../lib/toast";

type AccountData = {
  currency: string;
  package_active: boolean;
  package_purchase_status: string | null;
  package_expires_at: string | null;
  user: ShellUser & {
    country: string;
    created_at: string;
    referral_code: string;
    referral_url: string;
    avatar_url: string | null;
  };
  available_balance: string | number;
  deposit_balance: string | number;
  earning_balance: string | number;
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
  const refresh = useCallback(async () => {
    try {
      setAccount(await api<AccountData>("/dashboard"));
      setError("");
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Account information could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);
  useLiveRefresh(refresh, { eventName: WALLET_UPDATED_EVENT });

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
  return formatUsd(value);
}

export function ProfilePage() {
  const { account, setAccount, loading, error } = useAccount();
  const photoInput = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [photoMessage, setPhotoMessage] = useState("");
  const [referralMessage, setReferralMessage] = useState("");
  const accountIsActive = Boolean(
    account?.package_active &&
    account.user.email_verified &&
    account.user.status === "ACTIVE",
  );
  const accountStatusLabel = account?.user.status === "SUSPENDED" || account?.user.status === "BANNED"
    ? account.user.status.replaceAll("_", " ")
    : !account?.user.email_verified
      ? "Pending verification"
      : accountIsActive
        ? "Active"
        : "Inactive";

  async function uploadPhoto(file: File | undefined) {
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      const message = "JPEG, PNG, or WebP images are supported.";
      setPhotoMessage(message);
      showToast({ title: "Unsupported image", description: message, variant: "destructive" });
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      const message = "Choose an image that is 5 MB or smaller.";
      setPhotoMessage(message);
      showToast({ title: "Image is too large", description: message, variant: "destructive" });
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
      showToast({ title: "Profile photo updated", description: "Your new profile photo is ready.", variant: "success" });
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "Profile photo could not be uploaded.";
      setPhotoMessage(message);
      showToast({ title: "Profile photo upload failed", description: message, variant: "destructive" });
    } finally {
      setUploading(false);
      if (photoInput.current) photoInput.current.value = "";
    }
  }

  async function copyReferralLink() {
    if (!account) return;
    try {
      await navigator.clipboard.writeText(account.user.referral_url);
      const message = "Referral link copied.";
      setReferralMessage(message);
      showToast({ title: "Referral link copied", description: message, variant: "success" });
    } catch {
      const message = "Could not copy the referral link. Select and copy it manually.";
      setReferralMessage(message);
      showToast({ title: "Could not copy link", description: message, variant: "destructive" });
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
                  <Badge className={`profile-status-badge ${accountIsActive ? "is-active" : "is-inactive"}`} variant="outline">{accountStatusLabel}</Badge>
                  <Badge className={`profile-status-badge ${account.user.email_verified ? "is-verified" : "is-unverified"}`} variant="outline">
                    {account.user.email_verified ? "Email verified" : "Email not verified"}
                  </Badge>
                </div>
                {account.user.email_verified && account.user.status === "ACTIVE" && !accountIsActive && (
                  <p className="profile-activation-note">
                    {account.package_purchase_status === "PENDING"
                      ? "Your account is inactive while your package payment is under review. Earning access activates after approval."
                      : "Your email is verified, but your account is inactive. Buy an earning package to activate your account and start earning."}
                    {account.package_purchase_status !== "PENDING" && (
                      <>{" "}<Link href="/packages">View packages <ArrowUpRight size={13} aria-hidden="true" /></Link></>
                    )}
                  </p>
                )}
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
              <p>Total wallet balance</p>
              <strong>{formatMoney(account.available_balance, account.currency)}</strong>
              <small>Deposit and earnings combined</small>
            </Card>
            <Card className="profile-balance-card">
              <span className="profile-balance-icon is-violet"><WalletCards size={17} /></span>
              <p>Deposit balance</p>
              <strong>{formatMoney(account.deposit_balance, account.currency)}</strong>
              <small>For package purchases only</small>
            </Card>
            <Card className="profile-balance-card">
              <span className="profile-balance-icon is-green"><ArrowUpRight size={17} /></span>
              <p>Earning balance</p>
              <strong>{formatMoney(account.earning_balance, account.currency)}</strong>
              <small>Can be withdrawn or used for packages</small>
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
                <div><strong>{account.stats.active_referrals}</strong><span>Package members</span></div>
                <div><strong>{formatMoney(account.stats.referral_earnings, account.currency)}</strong><span>Referral earnings</span></div>
              </div>
              <p className="profile-pending-referral">Pending referral earnings <strong>{formatMoney(account.stats.pending_referral_earnings, account.currency)}</strong></p>
            </Card>

            <Card className="panel profile-package-card">
              <span className="profile-package-icon"><WalletCards size={19} /></span>
              <p className="eyebrow">EARNING ACCESS</p>
              <h2>
                {account.user.status !== "ACTIVE"
                  ? "Account access unavailable"
                  : accountIsActive
                  ? "Your earning package is active"
                  : account.package_purchase_status === "PENDING"
                    ? "Package payment under review"
                    : "Activate your earning package"}
              </h2>
              <p>
                {account.user.status !== "ACTIVE"
                  ? "Please contact WorkBit support to resolve your account status before using earning features."
                  : accountIsActive
                  ? `Your package payment has been approved. Your account is active and earning offers are unlocked${account.package_expires_at ? ` until ${new Date(account.package_expires_at).toLocaleDateString()}` : ""}.`
                  : account.package_purchase_status === "PENDING"
                    ? "Your account will become active and earning offers will unlock after an admin verifies your payment."
                    : "Submit your bKash or Nagad payment reference. Your account becomes active and earning offers unlock after an admin verifies your payment."}
              </p>
              {!accountIsActive && account.package_purchase_status !== "PENDING" && (
                <Button className="profile-settings-link" variant="outline" asChild><Link href="/packages">View packages <ArrowUpRight size={15} /></Link></Button>
              )}
            </Card>
          </section>

          <Card className="panel profile-account-card">
            <div className="profile-section-heading">
              <div><p className="eyebrow">ACCOUNT DETAILS</p><h2>Your information</h2></div>
            </div>
            <dl className="account-details">
              <div><dt>Account status</dt><dd>{accountStatusLabel}</dd></div>
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
  const { account, setAccount, loading, error } = useAccount();
  const [verificationBusy, setVerificationBusy] = useState(false);
  const [verificationMessage, setVerificationMessage] = useState("");
  const [name, setName] = useState("");
  const [nameBusy, setNameBusy] = useState(false);
  const [nameMessage, setNameMessage] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordBusy, setPasswordBusy] = useState(false);
  const [passwordMessage, setPasswordMessage] = useState("");

  useEffect(() => {
    if (account) setName(account.user.full_name);
  }, [account]);

  async function updateName(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNameBusy(true);
    setNameMessage("");
    try {
      const updated = await api<ShellUser>("/profile/account", {
        method: "PATCH",
        body: JSON.stringify({ full_name: name }),
      });
      setAccount((current) =>
        current
          ? {
              ...current,
              user: {
                ...current.user,
                full_name: updated.full_name,
                status: updated.status,
                email_verified: updated.email_verified,
                avatar_url: updated.avatar_url ?? null,
              },
            }
          : current,
      );
      const nameUpdated = "Your name has been updated.";
      setNameMessage(nameUpdated);
      showToast({ title: "Profile updated", description: nameUpdated, variant: "success" });
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "Your name could not be updated.";
      setNameMessage(message);
      showToast({ title: "Profile update failed", description: message, variant: "destructive" });
    } finally {
      setNameBusy(false);
    }
  }

  async function updatePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (newPassword !== confirmPassword) {
      const message = "New passwords do not match.";
      setPasswordMessage(message);
      showToast({ title: "Password mismatch", description: message, variant: "destructive" });
      return;
    }

    setPasswordBusy(true);
    setPasswordMessage("");
    try {
      await api<ShellUser>("/profile/account", {
        method: "PATCH",
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword,
        }),
      });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      const successMessage = "Your password has been changed.";
      setPasswordMessage(successMessage);
      showToast({ title: "Password updated", description: successMessage, variant: "success" });
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "Your password could not be changed.";
      setPasswordMessage(message);
      showToast({ title: "Password update failed", description: message, variant: "destructive" });
    } finally {
      setPasswordBusy(false);
    }
  }

  async function resendVerification() {
    setVerificationBusy(true);
    setVerificationMessage("");
    try {
      const result = await api<{ message: string }>("/auth/resend-verification", { method: "POST" });
      setVerificationMessage(result.message);
      showToast({ title: "Verification code sent", description: result.message, variant: "success", kind: "otp-sent" });
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "The verification request could not be sent.";
      setVerificationMessage(message);
      showToast({ title: "Verification request failed", description: message, variant: "destructive" });
    } finally {
      setVerificationBusy(false);
    }
  }

  return (
    <Shell user={account?.user}>
      <header className="top">
        <div>
          <p className="eyebrow">PREFERENCES & SECURITY</p>
          <h1>Account settings</h1>
          <p className="muted">Update your profile details and keep your account secure.</p>
        </div>
      </header>
      <AccountState loading={loading} error={error} />
      {account && (
        <Card className="panel settings-card">
          <section className="settings-section" aria-labelledby="settings-name-heading">
            <div className="settings-section-heading">
              <span className="settings-section-icon"><UserRound size={19} aria-hidden="true" /></span>
              <div>
                <h2 id="settings-name-heading">Personal information</h2>
                <p className="panel-subtitle">Update the name shown on your WorkBit account.</p>
              </div>
            </div>
            <form className="settings-form" onSubmit={updateName}>
              <label htmlFor="settings-full-name">Full name</label>
              <Input
                id="settings-full-name"
                name="full_name"
                autoComplete="name"
                minLength={2}
                maxLength={120}
                required
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
              <Button className="primary settings-submit" type="submit" disabled={nameBusy || name.trim() === account.user.full_name}>
                <Save size={16} aria-hidden="true" />
                {nameBusy ? "Saving…" : "Save name"}
              </Button>
              {nameMessage && <p className="settings-feedback" role="status">{nameMessage}</p>}
            </form>
          </section>
          <div className="settings-divider" />
          <section className="settings-section" aria-labelledby="settings-password-heading">
            <div className="settings-section-heading">
              <span className="settings-section-icon"><KeyRound size={19} aria-hidden="true" /></span>
              <div>
                <h2 id="settings-password-heading">Change password</h2>
                <p className="panel-subtitle">Use your current password to set a new one. New passwords need at least 12 characters with uppercase, lowercase, and a number.</p>
              </div>
            </div>
            <form className="settings-form settings-password-form" onSubmit={updatePassword}>
              <label htmlFor="settings-current-password">Current password</label>
              <PasswordInput
                id="settings-current-password"
                name="current_password"
                autoComplete="current-password"
                maxLength={128}
                required
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
              />
              <label htmlFor="settings-new-password">New password</label>
              <PasswordInput
                id="settings-new-password"
                name="new_password"
                autoComplete="new-password"
                minLength={12}
                maxLength={128}
                required
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
              />
              <label htmlFor="settings-confirm-password">Confirm new password</label>
              <PasswordInput
                id="settings-confirm-password"
                name="confirm_password"
                autoComplete="new-password"
                minLength={12}
                maxLength={128}
                required
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
              />
              <Button className="primary settings-submit" type="submit" disabled={passwordBusy}>
                <KeyRound size={16} aria-hidden="true" />
                {passwordBusy ? "Updating…" : "Update password"}
              </Button>
              {passwordMessage && <p className="settings-feedback" role="status">{passwordMessage}</p>}
            </form>
          </section>
          <div className="settings-divider" />
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
            <Button className="primary" type="button" onClick={resendVerification} disabled={verificationBusy}>
              {verificationBusy ? "Requesting…" : "Resend verification email"}
            </Button>
          )}
          {verificationMessage && <Alert className="inline-status" role="status"><AlertDescription>{verificationMessage}</AlertDescription></Alert>}
          <Button className="text-link" variant="link" asChild><Link href="/forgot-password">Forgot your password? Reset by email →</Link></Button>
        </Card>
      )}
    </Shell>
  );
}
