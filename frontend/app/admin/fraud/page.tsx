import type { Metadata } from "next";
import { AdminFraud } from "../../../components/admin-fraud";

export const metadata: Metadata = {
  title: "Fraud management | WorkBit Admin",
};

export default function AdminFraudPage() {
  return <AdminFraud />;
}
