# Display ad network setup

The display providers are intentionally separate from the offer/reward pipeline. Each placement's activation requirements and page location are listed below: some require an explicit `ENABLED` flag, while others are enabled by a placement key or currently use a configured adapter. Provider inventory and ad fill are controlled by each publisher account, so a rendered placement can still be empty when a provider has no eligible ad to serve.

| Provider | Frontend adapter | Required display configuration | Current behavior |
| --- | --- | --- | --- |
| Adsterra | `frontend/components/ads/providers/adsterra/banner.tsx` | No environment variables; the current placement IDs are configured in the adapter | Social bar, native banner, responsive banners, and desktop side placements on `/offers` |
| AmanahAds | `frontend/components/ads/providers/amanahads/placement.tsx` | `NEXT_PUBLIC_AMANAHADS_INSTANCE_KEY` | Iframe placements on `/offers`; also offers an explicitly user-opened popup |
| A-ADS | `frontend/components/ads/providers/a-ads/banner.tsx` | `NEXT_PUBLIC_AADS_ENABLED=true`, `NEXT_PUBLIC_AADS_UNIT_ID`; `NEXT_PUBLIC_AADS_UNIT_SIZE` is optional | Iframe banner on the public homepage and `/offers` |
| Coinzilla | `frontend/components/ads/providers/coinzilla/native.tsx` | Coinzilla verification meta tag in `frontend/app/layout.tsx`; `NEXT_PUBLIC_COINZILLA_ENABLED=true`, `NEXT_PUBLIC_COINZILLA_ZONE_ID` | Coinzilla native widget on `/offers` |
| Cointraffic | `frontend/components/ads/providers/cointraffic/banner.tsx` | `NEXT_PUBLIC_COINTRAFFIC_ENABLED=true`, `NEXT_PUBLIC_COINTRAFFIC_TAG_SRC`; zone ID is optional | Provider unified code in its placement on `/offers` |
| PropellerAds | `frontend/components/ads/providers/propellerads/tag.tsx` | `NEXT_PUBLIC_PROPELLERADS_ENABLED=true`, `NEXT_PUBLIC_PROPELLERADS_TAG_SRC`; zone ID is optional | Provider-generated display script in its placement on `/offers` |
| Monetag | `frontend/components/ads/providers/monetag/tag.tsx` | `NEXT_PUBLIC_MONETAG_ENABLED=true`, `NEXT_PUBLIC_MONETAG_TAG_SRC` | Fixed display placement after the offerwall sections on `/offers`; zone ID is optional metadata |
| Offerwall.me Banner | `frontend/components/ads/providers/offerwall-me/banner.tsx` | `NEXT_PUBLIC_OFFERWALL_ME_BANNER_ENABLED=true`, `NEXT_PUBLIC_OFFERWALL_ME_BANNER_PLACEMENT_ID` | Direct banner script on `/offers`; 728x90 on desktop and 300x250 on smaller screens |
| Bitmedia | `frontend/components/ads/providers/bitmedia/banner.tsx` | `NEXT_PUBLIC_BITMEDIA_ENABLED=true`, `NEXT_PUBLIC_BITMEDIA_PLACEMENT_ID`; dimensions are optional | Bitmedia JavaScript placement on `/offers` |
| ProfitOn | `frontend/app/layout.tsx` | `NEXT_PUBLIC_PROFITON_DOMAIN_VERIFICATION` | Optional domain-verification meta tag only; no ProfitOn ad placement is enabled |

The provider-specific `*_API_KEY` and `*_POSTBACK_SECRET` entries in `.env.example` are reserved for a future server-side integration. They are not read by these display adapters and should remain empty until an approved API/postback flow is implemented and tested.

All display placements are disabled or hidden unless their required values above are present. For Docker Compose, put the public display settings in the repository-root `.env` file and rebuild the frontend image after changing them (for example, `docker compose up --build frontend`). Next.js embeds `NEXT_PUBLIC_*` values during the build, so setting them only on a running container will not enable an ad. For Vercel or another non-Docker deployment, set them in the frontend project's build environment and redeploy.

## Coinzilla setup

The Coinzilla publisher verification meta tag is included in the root document head. After Coinzilla approves the site and provides a native widget zone ID, configure `NEXT_PUBLIC_COINZILLA_ENABLED=true` and `NEXT_PUBLIC_COINZILLA_ZONE_ID` in the frontend build environment, then redeploy. The widget appears in its own section on `/offers`; impressions and clicks do not credit WorkBit rewards.

## Non-Docker deployment

Docker is not required. For the Vercel frontend project, add the following Production environment variables and redeploy:

```env
NEXT_PUBLIC_AADS_ENABLED=true
NEXT_PUBLIC_AADS_UNIT_ID=2460426
NEXT_PUBLIC_AADS_UNIT_SIZE=Adaptive
```

The A-ADS dashboard should verify `https://workbitbd.com/`. The unit is rendered on the public homepage so A-ADS can check it without requiring a signed-in session. It is also rendered on the offers page for signed-in users. Local development can use the same values in `frontend/.env.local`, then run `npm run dev` or `npm run build && npm start` from `frontend/`.

Do not turn display impressions or clicks into WorkBit wallet rewards unless the provider explicitly approves that product and supplies a verified server callback. The current adapters only monetize the platform's ad inventory; they never credit users.

WorkBit displays wallet balances and verified reward amounts as WBC equivalents at `1 WBC = ৳0.50`, using the current admin-configured USD/BDT withdrawal rate. This is a display conversion only: wallet ledger amounts remain USD, and the WBC equivalent can change when that rate changes. Only provider-confirmed survey/offer completions are eligible for wallet credit; ordinary banner impressions and clicks from A-ADS, Adsterra, or Monetag do not earn WBC.

For Monetag, configure a fixed display/banner placement tag from the approved publisher dashboard in `NEXT_PUBLIC_MONETAG_TAG_SRC` and its zone in `NEXT_PUBLIC_MONETAG_ZONE_ID`. The placement is rendered after the offerwall sections and before the WorkBit offer catalog; only the tag configured for that placement is loaded. Do not load Monetag Multitag or register its `sw.js` service worker for this setup, since those integrations can inject ads outside the designated section. The root layout retains the Monetag site-verification meta tag. The app removes a previously registered root `/sw.js` service worker so it cannot continue injecting ads after this change. Redeploy after updating environment variables.

For Cointraffic, add the following frontend Production environment variables in Vercel and redeploy:

```env
NEXT_PUBLIC_COINTRAFFIC_ENABLED=true
NEXT_PUBLIC_COINTRAFFIC_TAG_SRC=https://appsha-pnd.ctengine.io/js/script.js?wkey=D7BGqQ6AER
```

The supplied unified code is inserted inside the Cointraffic placement on `/offers`, not into the document head. Cointraffic says unified code loads all advertising formats activated for the website, so review the enabled placements in its dashboard before switching it on. The integration does not issue WorkBit rewards.

For Offerwall.me banners, set the following variables in the frontend Production environment and redeploy:

```env
NEXT_PUBLIC_OFFERWALL_ME_BANNER_ENABLED=true
NEXT_PUBLIC_OFFERWALL_ME_BANNER_PLACEMENT_ID=2lDAUVzFUGM2VZcA9hcRggp5XvKKQe
```

The placement ID is public and is taken from the generated banner code. WorkBit loads the `728x90` tag at desktop widths and the `300x250` tag on smaller screens, directly in the `/offers` page rather than inside a nested iframe. The `468x60` tag is not used by this responsive placement. The ad is display-only: impressions and clicks do not credit WorkBit rewards. Offerwall.me controls campaign eligibility and fill, so the slot can remain empty.

For ProfitOn domain verification, copy the verification value from the ProfitOn publisher dashboard into `NEXT_PUBLIC_PROFITON_DOMAIN_VERIFICATION` in the frontend deployment environment and redeploy. The value is emitted as a verification meta tag in the document head only when configured. This setting verifies domain ownership; it does not load ads. ProfitOn Native Banner placement remains separate and disabled until the site is approved and its generated placement tag has been reviewed and configured. Do not award WorkBit points for ad impressions or clicks.

## Admitad partner stores

The `/offers` page keeps Admitad in a separate **Shop partner stores** section. This is an affiliate-store directory, not an offerwall: purchases do not earn WorkBit rewards or cashback. The integration does not process Admitad commissions as user conversions.

Before enabling it:

1. Register and verify WorkBit as a publisher ad space in Admitad. Obtain the application `client_id` and `client_secret`, and request API access to `advcampaigns_for_website` and `deeplink_generator`.
2. Set `ADMITAD_WEBSITE_ID` to the approved WorkBit ad-space ID. Apply to each affiliate program in Admitad and wait for approval. WorkBit displays only active programs connected to that ad space, available for the visitor's country, and marked as allowing deeplinks.
3. Configure the backend environment and restart/redeploy the backend:

   ```env
   ADMITAD_ENABLED=true
   ADMITAD_CLIENT_ID=
   ADMITAD_CLIENT_SECRET=
   ADMITAD_WEBSITE_ID=
   ```

The backend obtains OAuth bearer tokens using the client-credentials flow and keeps credentials server-side. Never place the client secret in a `NEXT_PUBLIC_*` variable. A partner link is generated on demand through Admitad's Deeplink API and checked before it is sent to the browser. The `workbit-offers` SubID is non-personal and is used only to identify the page placement.

Admitad program terms, allowed traffic types, country eligibility, and commission approval remain controlled by Admitad and each advertiser. Do not promise users cashback or rewards, or turn affiliate commissions into wallet credits, unless both Admitad and the advertiser explicitly approve that incentive model and a separately verified conversion flow is implemented.

Official references: [Client authorization](https://developers.mitgo.com/hc/en-us/articles/34481345606546-Client-authorization), [API access settings](https://developers.mitgo.com/hc/en-us/articles/34481337268626-Help-on-access-settings), [Affiliate programs](https://developers.mitgo.com/hc/en-us/articles/34481349447058-Affiliate-programs), and [Deeplink generator](https://developers.mitgo.com/hc/en-us/articles/34481332881938-Deeplink-generator).
