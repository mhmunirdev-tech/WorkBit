import type { Metadata } from "next";
import { AdminEarningPackages } from "../../../components/admin-earning-packages";

export const metadata: Metadata = {
  title: "Earning packages | WorkBit Admin",
};

export default function AdminEarningPackagesPage() {
  return <AdminEarningPackages />;
}
