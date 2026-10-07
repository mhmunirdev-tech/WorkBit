import type { Metadata } from "next";
import { WithdrawalPage } from "../../components/withdrawals";

export const metadata: Metadata = {
  title: "Withdraw funds | WorkBit",
  robots: { index: false, follow: false },
};

export default function WithdrawRoute() {
  return <WithdrawalPage />;
}
