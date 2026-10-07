import type { Metadata } from "next";
import "./styles.css";
import "./dashboard.css";

export const metadata: Metadata = {
  title: "WorkBit | Work. Complete. Earn.",
  description: "A transparent marketplace for legitimate, provider-confirmed reward offers.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
