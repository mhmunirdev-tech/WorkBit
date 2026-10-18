import type { Metadata } from "next";
import { PackagesPage } from "../../components/packages-page";

export const metadata: Metadata = {
  title: "Earning packages | WorkBit",
};

export default function Page() {
  return <PackagesPage />;
}
