import type { Metadata } from "next";
import { FraudAppealForm } from "../../components/fraud-appeal-form";

export const metadata: Metadata = {
  title: "Request an account review | WorkBit",
  robots: { index: false, follow: false },
};

export default function FraudAppealPage() {
  return <FraudAppealForm />;
}
