import type { Metadata } from "next";
import { AdminProviderPerformance } from "../../../components/admin-provider-performance";

export const metadata: Metadata = {
  title: "Provider performance | WorkBit Admin",
};

export default function AdminProvidersPage() {
  return <AdminProviderPerformance />;
}
