import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

type UsdFormatOptions = Pick<Intl.NumberFormatOptions, "minimumFractionDigits" | "maximumFractionDigits">;

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
