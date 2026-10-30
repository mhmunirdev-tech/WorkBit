import type { Metadata } from "next";

import { Toaster } from "@/components/ui/toaster";
import { AnalyticsTracker } from "@/components/analytics-tracker";
import { MonetagServiceWorker } from "@/components/ads/providers/monetag/service-worker";
import "./styles.css";
import "./dashboard.css";
import "./admin-console.css";
import "./landing-modern.css";

export const metadata: Metadata = {
  title: "WorkBit | Work. Complete. Earn.",
  description: "A transparent marketplace for legitimate, provider-confirmed reward offers.",
  other: {
    "offerwall-verification": "ow-b83eb7451b057e11c305",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <Toaster />
        <AnalyticsTracker />
        <MonetagServiceWorker />
        {children}
      </body>
    </html>
  );
}
