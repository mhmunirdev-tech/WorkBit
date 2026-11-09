import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

type UsdFormatOptions = Pick<Intl.NumberFormatOptions, "minimumFractionDigits" | "maximumFractionDigits">;

export const WBC_VALUE_BDT = 0.5;

export function formatUsd(
  value: string | number,
  options: UsdFormatOptions = {},
): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
    ...options,
  }).format(Number(value));
}

export function formatWbcFromUsd(
  value: string | number,
  usdBdtRate: string | number | null | undefined,
): string | null {
  const amount = Number(value);
  const rate = Number(usdBdtRate);
  if (!Number.isFinite(amount) || !Number.isFinite(rate) || rate <= 0) return null;

  const wbcAmount = amount * rate / WBC_VALUE_BDT;

  return `${new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(wbcAmount)} WBC`;
}
