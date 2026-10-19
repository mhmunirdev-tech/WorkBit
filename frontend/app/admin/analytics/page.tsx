import type { Metadata } from "next";
import { AdminAnalytics } from "../../../components/admin-analytics";

export const metadata: Metadata = {
  title: "Analysis | WorkBit Admin",
};

export default function AdminAnalyticsPage() {
  return <AdminAnalytics />;
}
