import type { Metadata } from "next";

import { Toaster } from "@/components/ui/toaster";
import { AnalyticsTracker } from "@/components/analytics-tracker";
import { MonetagServiceWorkerCleanup } from "@/components/ads/providers/monetag/service-worker";
import "./styles.css";
import "./dashboard.css";
import "./admin-console.css";
import "./landing-modern.css";

export const metadata: Metadata = {
  title: "WorkBit | Work. Complete. Earn.",
  description: "A transparent marketplace for legitimate, provider-confirmed reward offers.",
  other: {
    "offerwall-verification": "ow-b83eb7451b057e11c305",
    coinzilla: "896b0c141c35883782f9a8f44ee465e4",
    monetag: "a7f8446bddb7a130f150e5d42760058b",
    ...(process.env.NEXT_PUBLIC_PROFITON_DOMAIN_VERIFICATION?.trim()
      ? { "profiton-domain-verification": process.env.NEXT_PUBLIC_PROFITON_DOMAIN_VERIFICATION.trim() }
      : {}),
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <Toaster />
        <AnalyticsTracker />
        <MonetagServiceWorkerCleanup />
        {children}
      </body>
    </html>
  );
}
