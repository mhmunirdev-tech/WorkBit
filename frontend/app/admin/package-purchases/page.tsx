import type { Metadata } from "next";
import { AdminPackagePurchases } from "../../../components/admin-package-purchases";

export const metadata: Metadata = {
  title: "Package payments | WorkBit Admin",
};

export default function Page() {
  return <AdminPackagePurchases />;
}
