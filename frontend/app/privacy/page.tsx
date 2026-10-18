import type { Metadata } from "next";
import { PolicyPage } from "../../components/policy-page";

export const metadata: Metadata = {
  title: "Privacy Policy | WorkBit",
  description: "How WorkBit handles account, wallet, offer, and technical information.",
};

export default function PrivacyPage() {
  return <PolicyPage policy="privacy" />;
}
