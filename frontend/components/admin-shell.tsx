"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import { Activity, Banknote, ImagePlus, LayoutDashboard, LogOut, Menu, PackageCheck, ShieldCheck, X, ArrowDownToLine, Settings2, Users } from "lucide-react";
import { api } from "../lib/api";
import { showToast } from "../lib/toast";
import { Avatar, AvatarFallback } from "./ui/avatar";
import { Button } from "./ui/button";

type AdminIdentity = {
  full_name: string;
  email: string;
  roles: string[];
};

const AdminIdentityContext = createContext<AdminIdentity | null>(null);

export function useAdminIdentity() {
  return useContext(AdminIdentityContext);
}

const navigationGroups = [
  {
    label: "Workspace",
    items: [
      { href: "/admin", label: "Overview", icon: LayoutDashboard },
      { href: "/admin/analytics", label: "Analysis", icon: Activity },
      { href: "/admin/users", label: "User registry", icon: Users },
    ],
  },
  {
    label: "Financial operations",
    items: [
      { href: "/admin/withdrawals", label: "Manual withdrawals", icon: Banknote },
      { href: "/admin/deposits", label: "Deposit requests", icon: ArrowDownToLine },
      { href: "/admin/package-purchases", label: "Package payments", icon: PackageCheck },
    ],
  },
  {
    label: "Platform setup",
    items: [
      { href: "/admin/packages", label: "Package settings", icon: Settings2 },
      { href: "/admin/banners", label: "Dashboard banners", icon: ImagePlus },
    ],
  },
];

export function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname().replace(/\/+$/, "") || "/";
  const [identity, setIdentity] = useState<AdminIdentity | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState("");

  useEffect(() => {
    if (pathname === "/admin/login") return;
    api<AdminIdentity>("/auth/admin/me")
      .then(setIdentity)
      .catch(() => {
        setIdentity(null);
      });
  }, [pathname]);

  async function logout() {
    setLoggingOut(true);
    setLogoutError("");
    try {
      await api<void>("/auth/admin/logout", { method: "POST" });
      showToast({ title: "Signed out", description: "You have been signed out.", variant: "success" });
      window.location.assign("/admin/login");
    } catch (error) {
      setLogoutError(error instanceof Error ? error.message : "Unable to sign out.");
      setLoggingOut(false);
    }
  }

  const initials = identity?.full_name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
  const currentPage = navigationGroups
    .flatMap((group) => group.items)
    .find((item) => pathname === item.href || (item.href !== "/admin" && pathname.startsWith(`${item.href}/`)));

  if (pathname === "/admin/login") return <>{children}</>;

  return (
    <AdminIdentityContext.Provider value={identity}>
      <main className="app-shell admin-app-shell">
      <Button
        className="mobile-menu-toggle"
        variant="ghost"
        size="icon"
        type="button"
        aria-label={menuOpen ? "Close admin navigation" : "Open admin navigation"}
        aria-expanded={menuOpen}
        aria-controls="admin-navigation"
        onClick={() => setMenuOpen((open) => !open)}
      >
        <span aria-hidden="true">{menuOpen ? <X /> : <Menu />}</span>
      </Button>
      {menuOpen && (
        <Button
          className="mobile-menu-backdrop"
          variant="ghost"
          type="button"
          aria-label="Close admin navigation"
          onClick={() => setMenuOpen(false)}
        />
      )}
      <aside className={`app-sidebar admin-sidebar${menuOpen ? " is-open" : ""}`}>
        <Link className="brand" href="/admin" onClick={() => setMenuOpen(false)}>
          <i aria-hidden="true">W</i> WorkBit
        </Link>
        <p className="tagline">Platform operations</p>
        <nav id="admin-navigation" aria-label="Admin navigation">
          {navigationGroups.map((group) => (
            <div className="admin-nav-group" key={group.label}>
              <p className="nav-caption">{group.label}</p>
              {group.items.map((item) => {
                const active = pathname === item.href ||
                  (item.href !== "/admin" && pathname.startsWith(`${item.href}/`));
                return (
                  <Link
                    className={`app-nav-link${active ? " is-active" : ""}`}
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    key={item.href}
                    onClick={() => setMenuOpen(false)}
                  >
                    <span className="nav-icon" aria-hidden="true"><item.icon size={17} /></span>
                    {item.label}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>
        <Link className="admin-user-space-link" href="/dashboard">
          <span className="nav-icon" aria-hidden="true"><ShieldCheck size={17} /></span>
          User dashboard
        </Link>
        <div className="sidebar-spacer" />
        {logoutError && <p className="logout-error" role="alert">{logoutError}</p>}
        <div className="sidebar-account">
          <Avatar className="user-avatar" aria-hidden="true">
            <AvatarFallback>{initials || "AD"}</AvatarFallback>
          </Avatar>
          <span className="sidebar-user-copy">
            <strong>{identity?.full_name || "Loading profile…"}</strong>
            <small>{identity?.roles.join(", ") || "Loading role…"}</small>
          </span>
          <Button
            className="logout-button"
            variant="ghost"
            size="icon"
            onClick={() => void logout()}
            disabled={loggingOut}
            type="button"
            aria-label={loggingOut ? "Signing out" : "Sign out"}
          >
            {loggingOut ? <span aria-hidden="true">…</span> : <LogOut size={16} />}
          </Button>
        </div>
      </aside>
      <section className="app-content admin-app-content">
        <header className="admin-console-topbar">
          <div>
            <p>WORKBIT <span>/</span> ADMIN CONSOLE</p>
            <strong>{currentPage?.label ?? "Operations"}</strong>
          </div>
          <div className="admin-console-session">
            <span className="admin-console-secure"><ShieldCheck size={15} /> Secure admin session</span>
            <span className="admin-console-user">{identity?.full_name || "Loading profile…"}</span>
          </div>
        </header>
        {children}
      </section>
      </main>
    </AdminIdentityContext.Provider>
  );
}
