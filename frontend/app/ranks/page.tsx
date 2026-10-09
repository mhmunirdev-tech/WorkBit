import type { Metadata } from "next";
import { RanksPage } from "../../components/ranks-page";

export const metadata: Metadata = {
  title: "Ranks | WorkBit",
  robots: { index: false, follow: false },
};

export default function RanksRoute() {
  return <RanksPage />;
}
