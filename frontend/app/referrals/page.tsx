import type { Metadata } from "next";
import { ReferralsPage } from "../../components/referrals-page";

export const metadata: Metadata = {
  title: "Referrals | WorkBit",
  robots: { index: false, follow: false },
};

export default function ReferralsRoute() {
  return <ReferralsPage />;
}
