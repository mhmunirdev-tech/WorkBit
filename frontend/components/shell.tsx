"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { ArrowRight, Bell, Coins } from "lucide-react";
import { formatUsd, formatWbcFromUsd } from "../lib/utils";
import { useLiveRefresh } from "../lib/use-live-refresh";
import {
  Award,
  Gift,
  Home,
  LogOut,
  Menu,
  PackageCheck,
  Settings,
  Sparkles,
  UserRound,
  Wallet,
  X,
} from "lucide-react";
import { api } from "../lib/api";
import { useLanguage } from "./language-provider";
import { showToast } from "../lib/toast";
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar";
import { Button } from "./ui/button";

export type ShellUser = {
  full_name: string;
  email: string;
  country?: string;
  status: string;
  email_verified: boolean;
  avatar_url?: string | null;
};

const ShellUserContext = createContext<ShellUser | null>(null);

export function useShellUser(): ShellUser | null {
  return useContext(ShellUserContext);
}

type WalletSnapshot = {
  available_balance: string | number;
  currency: string;
  usd_bdt_rate: string | number | null;
};

type RewardNotification = {
  id: string;
  reward_decision_id: string;
  status: string;
  title: string;
  message: string;
  reason: string | null;
  read_at: string | null;
  created_at: string;
};

type NotificationResponse = {
  items: RewardNotification[];
  unread_count: number;
};

let cachedWallet: WalletSnapshot | null = null;

export const WALLET_UPDATED_EVENT = "workbit:wallet-updated";

const pageTitles: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/offers": "Explore offers",
  "/packages": "Earning packages",
  "/ranks": "Ranks",
  "/wallet": "Wallet",
  "/transactions": "Transactions",
  "/rewards": "Reward history",
  "/profile": "Profile",
  "/settings": "Settings",
};

const navigation = [
  { href: "/dashboard", label: "Dashboard", icon: Home },
  { href: "/offers", label: "Explore offers", icon: Sparkles },
  { href: "/packages", label: "Earning packages", icon: PackageCheck },
  { href: "/ranks", label: "Ranks", icon: Award, prefetch: false },
  { href: "/wallet", label: "Wallet", icon: Wallet },
  { href: "/rewards", label: "Reward history", icon: Gift },
  { href: "/profile", label: "Profile", icon: UserRound },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Shell({
  children,
  user,
}: {
  children: React.ReactNode;
  user?: ShellUser | null;
}) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState("");
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [fetchedUser, setFetchedUser] = useState<ShellUser | null>(null);
  const [wallet, setWallet] = useState<WalletSnapshot | null>(() => cachedWallet);
  const [walletLoadError, setWalletLoadError] = useState(false);
  const [notifications, setNotifications] = useState<RewardNotification[]>([]);
  const [unreadNotifications, setUnreadNotifications] = useState(0);
  const [notificationError, setNotificationError] = useState("");
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const { language, setLanguage, t } = useLanguage();
  const accountMenuRef = useRef<HTMLDivElement>(null);
  const walletActive = useRef(false);
  const displayUser = user ?? fetchedUser;
  const initials = displayUser?.full_name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
  const pageTitle = t(
    pageTitles[pathname] ??
    (pathname.startsWith("/offers/") ? "Offer details" : "WorkBit"),
  );
  const availableBalance = wallet
    ? formatWbcFromUsd(wallet.available_balance, wallet.usd_bdt_rate) ?? formatUsd(wallet.available_balance)
    : null;

  useEffect(() => {
    if (user) return;
    let active = true;
    api<ShellUser>("/auth/me")
      .then((account) => {
        if (active) setFetchedUser(account);
      })
      .catch(() => {
        if (active) setFetchedUser(null);
      });
    return () => {
      active = false;
    };
  }, [user]);

  const refreshWallet = useCallback(async () => {
    try {
      const snapshot = await api<WalletSnapshot>("/wallet");
      cachedWallet = snapshot;
      if (walletActive.current) {
        setWallet(snapshot);
        setWalletLoadError(false);
      }
    } catch {
      if (walletActive.current && !cachedWallet) setWalletLoadError(true);
    }
  }, []);

  useEffect(() => {
    walletActive.current = true;
    void refreshWallet();
    return () => {
      walletActive.current = false;
    };
  }, [refreshWallet]);
  useLiveRefresh(refreshWallet, { eventName: WALLET_UPDATED_EVENT });

  const refreshNotifications = useCallback(async () => {
    try {
      const result = await api<NotificationResponse>("/notifications");
      setNotifications(result.items);
      setUnreadNotifications(result.unread_count);
      setNotificationError("");
    } catch (error) {
      setNotificationError(error instanceof Error ? error.message : "Notifications could not be loaded.");
    }
  }, []);

  useEffect(() => {
    void refreshNotifications();
  }, [refreshNotifications]);
  useLiveRefresh(refreshNotifications, {
    intervalMs: 30_000,
    eventName: WALLET_UPDATED_EVENT,
  });

  async function markNotificationRead(notification: RewardNotification) {
    if (notification.read_at) return;
    try {
      const updated = await api<RewardNotification>(
        `/notifications/${encodeURIComponent(notification.id)}/read`,
        { method: "POST" },
      );
      setNotifications((items) => items.map((item) => item.id === updated.id ? updated : item));
      setUnreadNotifications((count) => Math.max(0, count - 1));
    } catch (error) {
      setNotificationError(error instanceof Error ? error.message : "Notification could not be marked as read.");
    }
  }

  useEffect(() => {
    if (!accountMenuOpen) return;

    function closeOnOutsideClick(event: MouseEvent) {
      if (event.target instanceof Node && !accountMenuRef.current?.contains(event.target)) {
        setAccountMenuOpen(false);
      }
    }

    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setAccountMenuOpen(false);
    }

    document.addEventListener("mousedown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [accountMenuOpen]);

  async function logout() {
    setLoggingOut(true);
    setLogoutError("");
    setAccountMenuOpen(false);
    try {
      await api<void>("/auth/logout", { method: "POST" });
      showToast({ title: "Signed out", description: "You have been signed out.", variant: "success" });
      window.location.assign("/login");
    } catch (error) {
      setLogoutError(error instanceof Error ? error.message : "Unable to sign out.");
      setLoggingOut(false);
    }
  }

  return (
    <main className="app-shell">
      <Button
        className="mobile-menu-toggle"
        variant="ghost"
        size="icon"
        type="button"
        aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"}
        aria-expanded={menuOpen}
        aria-controls="dashboard-navigation"
        onClick={() => setMenuOpen((open) => !open)}
      >
        <span aria-hidden="true">{menuOpen ? <X /> : <Menu />}</span>
      </Button>
      {menuOpen && (
        <Button
          className="mobile-menu-backdrop"
          variant="ghost"
          type="button"
          aria-label="Close navigation menu"
          onClick={() => setMenuOpen(false)}
        />
      )}
      <aside className={`app-sidebar${menuOpen ? " is-open" : ""}`}>
        <Link className="brand" href="/dashboard" onClick={() => setMenuOpen(false)}>
          <i aria-hidden="true">W</i> WorkBit
        </Link>
        <p className="tagline">Work. Complete. Earn.</p>
        <p className="nav-caption">{t("YOUR SPACE")}</p>
        <nav id="dashboard-navigation" aria-label="Main navigation">
          {navigation.map((item) => {
            const active =
              pathname === item.href ||
              (item.href !== "/dashboard" && pathname.startsWith(`${item.href}/`));
            const icon = <span className="nav-icon" aria-hidden="true"><item.icon size={17} /></span>;
            return (
              <Link
                className={`app-nav-link${active ? " is-active" : ""}`}
                href={item.href}
                prefetch={item.prefetch}
                aria-current={active ? "page" : undefined}
                key={item.href}
                onClick={() => setMenuOpen(false)}
              >
                {icon}
                {t(item.label)}
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-spacer" />
        {logoutError && <p className="logout-error" role="alert">{logoutError}</p>}
        <div className="sidebar-account">
          <Avatar className="user-avatar" aria-hidden="true">
            {displayUser?.avatar_url && <AvatarImage src={displayUser.avatar_url} alt="" />}
            <AvatarFallback>{initials || "WB"}</AvatarFallback>
          </Avatar>
          <span className="sidebar-user-copy">
            <strong>{displayUser?.full_name || "Your account"}</strong>
            <small>{displayUser?.status?.replaceAll("_", " ") || "Member"}</small>
          </span>
          <Button className="logout-button" variant="ghost" size="icon" onClick={logout} disabled={loggingOut} type="button" aria-label={loggingOut ? "Signing out" : "Sign out"}>
            {loggingOut ? <span aria-hidden="true">…</span> : <LogOut size={16} />}
          </Button>
        </div>
      </aside>
      <section className="app-content">
        <header className="dashboard-topbar">
          <div className="dashboard-topbar-title">
            <p className="eyebrow">WORKBIT / MY SPACE</p>
            <h2>{pageTitle}</h2>
            <Link className="dashboard-mobile-brand" href="/dashboard" aria-label="WorkBit home">
              <i aria-hidden="true">W</i> WorkBit
            </Link>
          </div>
          <div className="dashboard-topbar-actions">
            <label className="language-control">
              <span className="sr-only">{t("Language")}</span>
              <select
                aria-label={t("Language")}
                className="language-selector"
                value={language}
                onChange={(event) => setLanguage(event.target.value === "bn" ? "bn" : "en")}
              >
                <option value="en">English</option>
                <option value="bn">বাংলা</option>
              </select>
            </label>
            <Link
              className={`dashboard-wallet-balance${walletLoadError ? " is-unavailable" : ""}`}
              href="/wallet"
              aria-label={wallet ? `Your rewards ${availableBalance}. Open wallet.` : walletLoadError ? "Rewards balance unavailable. Open wallet." : "Loading rewards balance."}
            >
              <span className="dashboard-wallet-icon"><Coins size={18} aria-hidden="true" /></span>
              <span className="dashboard-wallet-copy">
                <small>{t("Your Rewards")}</small>
                <strong>{availableBalance ?? (walletLoadError ? "Unavailable" : "Loading…")}</strong>
              </span>
              <ArrowRight className="dashboard-wallet-arrow" size={14} aria-hidden="true" />
            </Link>
            <div className="notification-menu">
              <button
                aria-label={`${t("Notifications")}${unreadNotifications ? `, ${unreadNotifications} unread` : ""}`}
                aria-expanded={notificationsOpen}
                aria-controls="reward-notifications"
                className="notification-trigger"
                onClick={() => setNotificationsOpen((open) => !open)}
                type="button"
              >
                <Bell size={18} aria-hidden="true" />
                {unreadNotifications > 0 && <span className="notification-count">{unreadNotifications > 99 ? "99+" : unreadNotifications}</span>}
              </button>
              {notificationsOpen && (
                <div className="notification-dropdown" id="reward-notifications" role="region" aria-label={t("Notifications")}>
                  <strong>{t("Notifications")}</strong>
                  {notificationError && <p className="notification-error" role="alert">{notificationError}</p>}
                  {!notificationError && notifications.length === 0 && <p>{t("No reward updates yet.")}</p>}
                  {notifications.map((notification) => (
                    <div
                      className={`notification-item${notification.read_at ? "" : " is-unread"}`}
                      key={notification.id}
                    >
                      <button
                        className="notification-content"
                        onClick={() => void markNotificationRead(notification)}
                        type="button"
                      >
                        <strong>{t(notification.title)}</strong>
                        <small>{t(notification.message)}</small>
                        {notification.reason && <small><b>{t("Reversal reason")}:</b> {notification.reason}</small>}
                        {!notification.read_at && <small>{t("Mark as read")}</small>}
                        <time dateTime={notification.created_at}>{new Date(notification.created_at).toLocaleString(language === "bn" ? "bn-BD" : "en-US")}</time>
                      </button>
                      {(notification.status === "REVERSED" || notification.status === "CHARGEBACK") && (
                        <Link href="/rewards" onClick={() => setNotificationsOpen(false)}>{t("View reward history")}</Link>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="dashboard-account-menu" ref={accountMenuRef}>
              <button
                className="dashboard-account-trigger"
                type="button"
                aria-label="Open account menu"
                aria-expanded={accountMenuOpen}
                aria-controls="dashboard-account-dropdown"
                onClick={() => setAccountMenuOpen((open) => !open)}
              >
                <span
                  className={`dashboard-avatar-wrap${displayUser?.status ? ` status-${displayUser.status.toLowerCase()}` : ""}`}
                  title={displayUser?.status ? `Account status: ${displayUser.status.replaceAll("_", " ")}` : undefined}
                >
                  <Avatar className="dashboard-topbar-avatar">
                    {displayUser?.avatar_url && <AvatarImage src={displayUser.avatar_url} alt="" />}
                    <AvatarFallback>{initials || "WB"}</AvatarFallback>
                  </Avatar>
                  {displayUser?.status && (
                    <span
                      className="dashboard-avatar-status"
                      role="img"
                      aria-label={`Account status: ${displayUser.status.replaceAll("_", " ")}`}
                    />
                  )}
                </span>
              </button>
              {accountMenuOpen && (
                <div className="dashboard-account-dropdown" id="dashboard-account-dropdown" aria-label="Account menu">
                  <div className="dashboard-account-identity">
                    <strong>{displayUser?.full_name || "Your account"}</strong>
                    <span>{displayUser?.email || "Email unavailable"}</span>
                  </div>
                  <Link href="/profile" onClick={() => setAccountMenuOpen(false)}>View profile</Link>
                  <Link href="/settings" onClick={() => setAccountMenuOpen(false)}>Account settings</Link>
                  <button type="button" onClick={() => void logout()} disabled={loggingOut}>
                    {loggingOut ? "Signing out…" : "Sign out"}
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>
        <ShellUserContext.Provider value={displayUser}>
          {children}
        </ShellUserContext.Provider>
      </section>
    </main>
  );
}
