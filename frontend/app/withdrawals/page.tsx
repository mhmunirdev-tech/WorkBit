import type { Metadata } from "next";
import { redirect } from "next/navigation";

export const metadata: Metadata = {
  title: "Withdrawal history | WorkBit",
  robots: { index: false, follow: false },
};

export default function WithdrawalsRoute() {
  redirect("/wallet#withdrawal-history");
}
