import type { Metadata } from "next";
import { redirect } from "next/navigation";

export const metadata: Metadata = {
  title: "Admin overview | WorkBit",
};

export default function AdminAnalyticsPage() {
  redirect("/admin");
}
