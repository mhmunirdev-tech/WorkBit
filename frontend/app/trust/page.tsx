import type { Metadata } from "next";
import { TrustCenter } from "../../components/trust-center";

export const metadata: Metadata = {
  title: "Trust center | WorkBit",
  description: "How WorkBit verifies rewards, processes withdrawals, and protects user privacy.",
};

export default function TrustRoute() {
  return <TrustCenter />;
}
