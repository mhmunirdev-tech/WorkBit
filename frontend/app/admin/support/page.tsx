import type { Metadata } from "next";
import { AdminSupport } from "../../../components/admin-support";

export const metadata: Metadata = { title: "Support tickets | WorkBit admin" };

export default function AdminSupportPage() {
  return <AdminSupport />;
}
