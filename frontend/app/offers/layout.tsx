import Script from "next/script";

export default function OffersLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const monetagEnabled = process.env.NEXT_PUBLIC_MONETAG_ENABLED?.toLowerCase() === "true";

  return (
    <>
      {monetagEnabled && (
        <Script
          id="monetag-multitag-303649"
          src="https://quge5.com/88/tag.min.js"
          data-zone="303649"
          data-cfasync="false"
          strategy="afterInteractive"
        />
      )}
      {children}
    </>
  );
}
