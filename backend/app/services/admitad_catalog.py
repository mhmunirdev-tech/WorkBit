from __future__ import annotations

import logging
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.config import settings
from app.integrations.offer_providers.admitad import (
    ADMITAD_API_ORIGIN,
    AdmitadConfigurationError,
    admitad_credentials,
)
from app.schemas.admitad import (
    AdmitadCampaign,
    AdmitadCampaignList,
    AdmitadCampaignRead,
    AdmitadCampaignsRead,
    AdmitadDeeplink,
    AdmitadTokenResponse,
)

logger = logging.getLogger(__name__)
API_SCOPE = "advcampaigns_for_website deeplink_generator"
CAMPAIGN_LIMIT = 100


class AdmitadCatalogService:
    async def list_campaigns(self, country: str) -> AdmitadCampaignsRead:
        client_id, client_secret, website_id = self._credentials()
        country = country.strip().upper()
        if len(country) != 2 or not country.isalpha() or country == "XX":
            raise HTTPException(503, "A valid country is required for Admitad partner deals.")

        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=False) as client:
                token = await self._access_token(client, client_id, client_secret)
                response = await client.get(
                    f"{ADMITAD_API_ORIGIN}/advcampaigns/website/{website_id}/",
                    params={
                        "limit": CAMPAIGN_LIMIT,
                        "offset": 0,
                        "connection_status": "active",
                        "has_tool": "deeplink",
                    },
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
                payload = AdmitadCampaignList.model_validate(response.json())
        except httpx.TimeoutException as error:
            raise HTTPException(503, "Admitad deals are taking too long to load.") from error
        except httpx.HTTPStatusError as error:
            self._log_upstream_status("campaign catalogue", error)
            raise HTTPException(
                503,
                "Admitad could not return partner deals. Check the API permissions and website approval.",
            ) from error
        except httpx.RequestError as error:
            raise HTTPException(503, "Admitad deals are temporarily unavailable.") from error
        except (ValueError, ValidationError) as error:
            raise HTTPException(502, "Admitad returned an invalid campaign catalogue.") from error

        campaigns = [
            self._campaign_read(campaign)
            for campaign in payload.results
            if self._is_eligible(campaign, country)
        ]
        return AdmitadCampaignsRead(campaigns=campaigns, total=len(campaigns))

    async def campaign_link(self, campaign_id: int, country: str) -> str:
        client_id, client_secret, website_id = self._credentials()
        if campaign_id <= 0:
            raise HTTPException(404, "Admitad campaign is unavailable.")
        country = country.strip().upper()
        if len(country) != 2 or not country.isalpha() or country == "XX":
            raise HTTPException(503, "A valid country is required for Admitad partner deals.")

        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=False) as client:
                token = await self._access_token(client, client_id, client_secret)
                campaign_response = await client.get(
                    f"{ADMITAD_API_ORIGIN}/advcampaigns/website/{website_id}/",
                    params={
                        "limit": CAMPAIGN_LIMIT,
                        "offset": 0,
                        "connection_status": "active",
                        "has_tool": "deeplink",
                    },
                    headers={"Authorization": f"Bearer {token}"},
                )
                campaign_response.raise_for_status()
                payload = AdmitadCampaignList.model_validate(campaign_response.json())
                campaign = next(
                    (
                        item
                        for item in payload.results
                        if item.id == campaign_id
                        and self._is_eligible(item, country)
                    ),
                    None,
                )
                if campaign is None or not self._valid_landing_url(campaign.site_url):
                    raise HTTPException(404, "Admitad campaign is unavailable.")

                link_response = await client.get(
                    f"{ADMITAD_API_ORIGIN}/deeplink/{website_id}/advcampaign/{campaign.id}/",
                    params={"subid": "workbit-offers", "ulp": campaign.site_url},
                    headers={"Authorization": f"Bearer {token}"},
                )
                link_response.raise_for_status()
                links = [
                    AdmitadDeeplink.model_validate(item)
                    for item in link_response.json()
                ]
        except HTTPException:
            raise
        except httpx.TimeoutException as error:
            raise HTTPException(503, "Admitad is taking too long to create a partner link.") from error
        except httpx.HTTPStatusError as error:
            self._log_upstream_status("deeplink request", error)
            raise HTTPException(
                503,
                "Admitad could not create a partner link. Check campaign approval and API permissions.",
            ) from error
        except httpx.RequestError as error:
            raise HTTPException(503, "Admitad partner links are temporarily unavailable.") from error
        except (TypeError, ValueError, ValidationError) as error:
            raise HTTPException(502, "Admitad returned an invalid partner link.") from error

        for item in links:
            if item.is_affiliate_product is False:
                continue
            if self._valid_admitad_link(item.link):
                return item.link
        raise HTTPException(502, "Admitad did not return a valid affiliate link.")

    async def _access_token(
        self,
        client: httpx.AsyncClient,
        client_id: str,
        client_secret: str,
    ) -> str:
        response = await client.post(
            f"{ADMITAD_API_ORIGIN}/token/",
            data={
                "client_id": client_id,
                "grant_type": "client_credentials",
                "scope": API_SCOPE,
            },
            auth=(client_id, client_secret),
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        token = AdmitadTokenResponse.model_validate(response.json())
        if token.token_type.lower() != "bearer":
            raise HTTPException(503, "Admitad returned an unsupported authorization type.")
        return token.access_token

    def _credentials(self) -> tuple[str, str, str]:
        try:
            return admitad_credentials()
        except AdmitadConfigurationError as error:
            raise HTTPException(503, str(error)) from error

    @staticmethod
    def _is_eligible(
        campaign: AdmitadCampaign,
        country: str | None = None,
    ) -> bool:
        if (
            campaign.status.lower() != "active"
            or campaign.connection_status.lower() != "active"
            or not campaign.allow_deeplink
            or not AdmitadCatalogService._valid_landing_url(campaign.site_url)
        ):
            return False
        action_countries = {
            item.strip().upper()
            for item in campaign.action_countries
            if item.strip()
        }
        return (
            country is None
            or campaign.allow_actions_all_countries
            or bool(action_countries.intersection({"*", "ALL"}))
            or not action_countries
            or country in action_countries
        )

    @staticmethod
    def _campaign_read(campaign: AdmitadCampaign) -> AdmitadCampaignRead:
        image_url = campaign.image
        if image_url and image_url.startswith("//"):
            image_url = f"https:{image_url}"
        if image_url and not AdmitadCatalogService._is_https_url(image_url):
            image_url = None
        return AdmitadCampaignRead(
            id=campaign.id,
            name=campaign.name,
            description=campaign.description[:1000],
            image_url=image_url,
            currency=campaign.currency[:16],
            actions=campaign.actions[:8],
        )

    @staticmethod
    def _valid_landing_url(value: str | None) -> bool:
        if not value or len(value) > 2000:
            return False
        try:
            parsed = urlsplit(value)
            return (
                parsed.scheme in {"http", "https"}
                and bool(parsed.hostname)
                and parsed.username is None
                and parsed.password is None
                and parsed.port in (None, 80, 443)
            )
        except ValueError:
            return False

    @staticmethod
    def _is_https_url(value: str) -> bool:
        try:
            parsed = urlsplit(value)
            return (
                parsed.scheme == "https"
                and bool(parsed.hostname)
                and parsed.username is None
                and parsed.password is None
                and parsed.port in (None, 443)
            )
        except ValueError:
            return False

    @staticmethod
    def _valid_admitad_link(value: str) -> bool:
        try:
            parsed = urlsplit(value)
            return (
                parsed.scheme == "https"
                and parsed.hostname == "ad.admitad.com"
                and parsed.port in (None, 443)
                and parsed.username is None
                and parsed.password is None
                and parsed.path.startswith("/goto/")
            )
        except ValueError:
            return False

    @staticmethod
    def _log_upstream_status(operation: str, error: httpx.HTTPStatusError) -> None:
        logger.warning(
            "Admitad %s failed with HTTP status %s.",
            operation,
            error.response.status_code,
        )


admitad_catalog_service = AdmitadCatalogService()
