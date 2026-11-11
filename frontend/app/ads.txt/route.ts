const EZOIC_ADSTXT_MANAGER = "https://srv.adstxtmanager.com/19390";

export const dynamic = "force-dynamic";

export function GET() {
  const domain = process.env.EZOIC_ADSTXT_DOMAIN?.trim().toLowerCase();
  const domainPattern = /^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/;

  if (!domain || !domainPattern.test(domain)) {
    return new Response("EZOIC_ADSTXT_DOMAIN must be set to a valid site domain.\n", {
      status: 503,
      headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" },
    });
  }

  return Response.redirect(`${EZOIC_ADSTXT_MANAGER}/${domain}`, 301);
}
