import type { Metadata } from "next";
import { VerifyEmail } from "../../components/verify-email";

export const metadata: Metadata = {
  title: "Verify email | WorkBit",
  robots: { index: false, follow: false },
};

export default async function VerifyEmailPage({
  searchParams,
}: {
  searchParams: Promise<{ email?: string | string[] }>;
}) {
  const { email } = await searchParams;
  return <VerifyEmail email={typeof email === "string" ? email : ""} />;
}
