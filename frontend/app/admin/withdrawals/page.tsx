import type { Metadata } from "next";
import { AdminWithdrawals } from "../../../components/admin-withdrawals";

export const metadata: Metadata = {
  title: "Manual withdrawals | WorkBit Admin",
};

export default function AdminWithdrawalsPage() {
  return <AdminWithdrawals />;
}
