import type { Metadata } from "next";
import { VerifyEmail } from "../../components/verify-email";

export const metadata: Metadata = {
  title: "Verify email | WorkBit",
  robots: { index: false, follow: false },
};

export default async function VerifyEmailPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string | string[] }>;
}) {
  const { token } = await searchParams;
  return <VerifyEmail token={typeof token === "string" ? token : null} />;
}
