/* eslint @next/next/no-before-interactive-script-outside-document: off -- App Router requires this in the root layout. */
import Script from "next/script";

export function EzoicScripts() {
  if (process.env.NEXT_PUBLIC_EZOIC_ENABLED?.toLowerCase() !== "true") return null;

  return (
    <>
      <Script
        data-cfasync="false"
        src="https://cmp.gatekeeperconsent.com/min.js"
        strategy="beforeInteractive"
      />
      <Script
        data-cfasync="false"
        src="https://the.gatekeeperconsent.com/cmp.min.js"
        strategy="beforeInteractive"
      />
      <Script
        async
        src="https://www.ezojs.com/ezoic/sa.min.js"
        strategy="beforeInteractive"
      />
      <Script id="ezoic-standalone-init" strategy="beforeInteractive">
        {`window.ezstandalone = window.ezstandalone || {}; window.ezstandalone.cmd = window.ezstandalone.cmd || [];`}
      </Script>
      <Script
        src="https://ezoicanalytics.com/analytics.js"
        strategy="beforeInteractive"
      />
    </>
  );
}
