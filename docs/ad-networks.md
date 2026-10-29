# Display ad network setup

The display providers are intentionally separate from the offer/reward pipeline. Every provider is disabled by default and every frontend adapter returns nothing until its `NEXT_PUBLIC_*_ENABLED` flag and placement configuration are present.

| Provider | Frontend adapter | Main configuration | Current behavior |
| --- | --- | --- | --- |
| A-ADS | `frontend/components/ads/providers/a-ads/banner.tsx` | `NEXT_PUBLIC_AADS_UNIT_ID` | A-ADS iframe banner |
| Coinzilla | `frontend/components/ads/providers/coinzilla/native.tsx` | `NEXT_PUBLIC_COINZILLA_ZONE_ID` | Coinzilla native widget |
| Cointraffic | `frontend/components/ads/providers/cointraffic/banner.tsx` | `NEXT_PUBLIC_COINTRAFFIC_TAG_SRC` | Provider-generated display script |
| PropellerAds | `frontend/components/ads/providers/propellerads/tag.tsx` | `NEXT_PUBLIC_PROPELLERADS_TAG_SRC` | Provider-generated display script |
| Monetag | `frontend/components/ads/providers/monetag/tag.tsx` | `NEXT_PUBLIC_MONETAG_TAG_SRC` | Provider-generated display script |
| Bitmedia | `frontend/components/ads/providers/bitmedia/banner.tsx` | `NEXT_PUBLIC_BITMEDIA_PLACEMENT_ID` | Bitmedia JavaScript placement |

The provider-specific `*_API_KEY` and `*_POSTBACK_SECRET` entries in `.env.example` are reserved for a future server-side integration. They are not read by these display adapters and should remain empty until an approved API/postback flow is implemented and tested.

Do not turn display impressions or clicks into WorkBit wallet rewards unless the provider explicitly approves that product and supplies a verified server callback. The current adapters only monetize the platform's ad inventory; they never credit users.
