import type { Metadata } from "next";
import { AdminBanners } from "../../../components/admin-banners";

export const metadata: Metadata = {
  title: "Dashboard banners | WorkBit Admin",
};

export default function AdminBannersPage() {
  return <AdminBanners />;
}
