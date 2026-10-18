import type { Metadata } from "next";
import { PolicyPage } from "../../components/policy-page";

export const metadata: Metadata = {
  title: "Reward Policy | WorkBit",
  description: "WorkBit offer eligibility, provider verification, and reward rules.",
};

export default function RewardPolicyPage() {
  return <PolicyPage policy="reward-policy" />;
}
