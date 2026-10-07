import type { Metadata } from "next";
import { ResetPassword } from "../../components/reset-password";

export const metadata: Metadata = {
  title: "Reset password | WorkBit",
  robots: { index: false, follow: false },
};

export default async function ResetPasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string | string[] }>;
}) {
  const { token } = await searchParams;
  return <ResetPassword token={typeof token === "string" ? token : null} />;
}
