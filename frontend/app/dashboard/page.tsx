import type { Metadata } from "next";
import { Dashboard } from "../../components/dashboard";

export const metadata: Metadata = {
  title: "Dashboard | WorkBit",
  robots: { index: false, follow: false },
};

export default function DashboardPage() {
  return <Dashboard />;
}
