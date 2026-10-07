import type { Metadata } from "next";
import { WithdrawalPage } from "../../components/withdrawals";

export const metadata: Metadata = {
  title: "Withdrawal history | WorkBit",
  robots: { index: false, follow: false },
};

export default function WithdrawalsRoute() {
  return <WithdrawalPage historyOnly />;
}
