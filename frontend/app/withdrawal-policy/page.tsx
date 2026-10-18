import type { Metadata } from "next";
import { PolicyPage } from "../../components/policy-page";

export const metadata: Metadata = {
  title: "Withdrawal Policy | WorkBit",
  description: "WorkBit withdrawable balances, request requirements, and review process.",
};

export default function WithdrawalPolicyPage() {
  return <PolicyPage policy="withdrawal-policy" />;
}
