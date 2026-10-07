"use client";

import { useParams } from "next/navigation";
import { OfferDetailPage } from "../../../components/offers";

export default function OfferDetailRoute() {
  const params = useParams<{ id: string }>();
  return <OfferDetailPage id={params.id} />;
}
