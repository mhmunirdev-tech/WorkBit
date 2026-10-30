import Script from "next/script";

export default function OffersLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const monetagEnabled = process.env.NEXT_PUBLIC_MONETAG_ENABLED?.toLowerCase() === "true";

  return (
    <>
      {monetagEnabled && (
        <>
          <Script id="monetag-vignette-12154839" strategy="beforeInteractive">
            {`(function(s){s.dataset.zone='12154839',s.src='https://n6wxm.com/vignette.min.js'})([document.documentElement, document.body].filter(Boolean).pop().appendChild(document.createElement('script')));`}
          </Script>
          <Script
            id="monetag-multitag-303649"
            src="https://quge5.com/88/tag.min.js"
            data-zone="303649"
            data-cfasync="false"
            strategy="beforeInteractive"
          />
          <Script id="monetag-tag-12154837" strategy="beforeInteractive">
            {`(function(s){s.dataset.zone='12154837',s.src='https://al5sm.com/tag.min.js'})([document.documentElement, document.body].filter(Boolean).pop().appendChild(document.createElement('script')));`}
          </Script>
          <Script id="monetag-tag-12154836" strategy="beforeInteractive">
            {`(function(s){s.dataset.zone='12154836',s.src='https://al5sm.com/tag.min.js'})([document.documentElement, document.body].filter(Boolean).pop().appendChild(document.createElement('script')));`}
          </Script>
        </>
      )}
      {children}
    </>
  );
}
