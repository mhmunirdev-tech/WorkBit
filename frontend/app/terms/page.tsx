import type { Metadata } from "next";
import { PolicyPage } from "../../components/policy-page";

export const metadata: Metadata = {
  title: "Terms of Service | WorkBit",
  description: "WorkBit account, package, offer, wallet, and service terms.",
};

export default function TermsPage() {
  return <PolicyPage policy="terms" />;
}
