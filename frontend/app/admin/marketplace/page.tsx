import type { Metadata } from "next";

import { AdminMarketplace } from "../../../components/admin-marketplace";

export const metadata: Metadata = {
  title: "Marketplace | WorkBit Admin",
};

export default function AdminMarketplacePage() {
  return <AdminMarketplace />;
}
