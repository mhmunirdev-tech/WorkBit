# Display ad network setup

The display providers are intentionally separate from the offer/reward pipeline. Every provider is disabled by default and every frontend adapter returns nothing until its `NEXT_PUBLIC_*_ENABLED` flag and placement configuration are present.

| Provider | Frontend adapter | Main configuration | Current behavior |
| --- | --- | --- | --- |
| A-ADS | `frontend/components/ads/providers/a-ads/banner.tsx` | `NEXT_PUBLIC_AADS_UNIT_ID` | A-ADS iframe banner |
| Coinzilla | `frontend/components/ads/providers/coinzilla/native.tsx` | `NEXT_PUBLIC_COINZILLA_ZONE_ID` | Coinzilla native widget |
| Cointraffic | `frontend/components/ads/providers/cointraffic/banner.tsx` | `NEXT_PUBLIC_COINTRAFFIC_TAG_SRC` | Provider-generated display script |
| PropellerAds | `frontend/components/ads/providers/propellerads/tag.tsx` | `NEXT_PUBLIC_PROPELLERADS_TAG_SRC` | Provider-generated display script |
| Monetag | `frontend/components/ads/providers/monetag/multitag.tsx` | `NEXT_PUBLIC_MONETAG_ENABLED` | Multitag scripts loaded on `/offers` and publisher-provided `frontend/public/sw.js` service worker |
| Bitmedia | `frontend/components/ads/providers/bitmedia/banner.tsx` | `NEXT_PUBLIC_BITMEDIA_PLACEMENT_ID` | Bitmedia JavaScript placement |

The provider-specific `*_API_KEY` and `*_POSTBACK_SECRET` entries in `.env.example` are reserved for a future server-side integration. They are not read by these display adapters and should remain empty until an approved API/postback flow is implemented and tested.

## Non-Docker deployment

Docker is not required. For the Vercel frontend project, add the following Production environment variables and redeploy:

```env
NEXT_PUBLIC_AADS_ENABLED=true
NEXT_PUBLIC_AADS_UNIT_ID=2460426
NEXT_PUBLIC_AADS_UNIT_SIZE=Adaptive
```

The A-ADS dashboard should verify `https://workbitbd.com/`. The unit is rendered on the public homepage so A-ADS can check it without requiring a signed-in session. It is also rendered on the offers page for signed-in users. Local development can use the same values in `frontend/.env.local`, then run `npm run dev` or `npm run build && npm start` from `frontend/`.

Do not turn display impressions or clicks into WorkBit wallet rewards unless the provider explicitly approves that product and supplies a verified server callback. The current adapters only monetize the platform's ad inventory; they never credit users.

For Monetag Multitag, keep the publisher-provided `sw.js` in `frontend/public/` so it is served at `/sw.js` on the deployed website. The Multitag download replaces the earlier site-verification worker and contains the Multitag zone ID; site verification is retained through the Monetag meta tag in the root layout. The frontend registers the worker and loads the Multitag scripts only on `/offers` when `NEXT_PUBLIC_MONETAG_ENABLED=true`. Redeploy after updating the public file or environment variables.
