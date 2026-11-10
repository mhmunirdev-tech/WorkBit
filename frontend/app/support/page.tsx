import type { Metadata } from "next";
import { SupportPage } from "../../components/support-page";

export const metadata: Metadata = {
  title: "Support | WorkBit",
  robots: { index: false, follow: false },
};

export default function SupportRoute() {
  return <SupportPage />;
}
