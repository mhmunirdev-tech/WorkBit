import type { Metadata } from "next";
import { redirect } from "next/navigation";

export const metadata: Metadata = {
  title: "Withdraw funds | WorkBit",
  robots: { index: false, follow: false },
};

export default function WithdrawRoute() {
  redirect("/wallet#withdraw-request");
}
