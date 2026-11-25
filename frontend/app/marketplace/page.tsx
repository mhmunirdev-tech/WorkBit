import type { Metadata } from "next";

import { MarketplacePage } from "../../components/marketplace-page";

export const metadata: Metadata = {
  title: "Marketplace | WorkBit",
};

export default function Page() {
  return <MarketplacePage />;
}
