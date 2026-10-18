import { redirect } from "next/navigation";
import { DepositPage } from "../../components/deposit-page";

export default async function DepositRoute({
  searchParams,
}: {
  searchParams: Promise<{ package?: string | string[] }>;
}) {
  const params = await searchParams;
  const packageCode = Array.isArray(params.package) ? params.package[0] : params.package;
  if (!packageCode) redirect("/packages");
  return <DepositPage packageCode={packageCode} />;
}
