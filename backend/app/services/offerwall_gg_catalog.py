from __future__ import annotations

from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.offer_providers.offerwall_gg import (
    OFFERWALL_GG_SLUG,
)
from app.models import User
from app.schemas.offerwall_gg import (
    OfferwallGGApiResponse,
    OfferwallGGOfferRead,
    OfferwallGGOffersRead,
)
from app.services.rewards import reward_decision_service

API_OFFERS_URL = "https://offerwall.gg/api/v1/offers"


class OfferwallGGCatalogService:
    async def list_offers(
        self,
        db: Session,
        user: User,
        country: str,
        device: str,
        page: int,
        limit: int,
        search: str | None,
        category: str | None,
    ) -> OfferwallGGOffersRead:
        if not settings.offerwall_gg_enabled:
            raise HTTPException(503, "Offerwall.GG integration is disabled.")

        public_key = (settings.offerwall_gg_public_key or "").strip()
        secret_key = settings.offerwall_gg_secret_key or ""
        if not public_key or len(public_key) != 32 or not secret_key:
            raise HTTPException(503, "Offerwall.GG credentials are not configured.")

        params: dict[str, str | int] = {
            "appId": public_key,
            "userId": user.id,
            "country": country.upper(),
            "device": device,
            "page": page,
            "limit": limit,
            "sort": "payout",
        }
        if search:
            params["search"] = search
        if category:
            params["category"] = category

        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=False) as client:
                response = await client.get(
                    API_OFFERS_URL,
                    params=params,
                    headers={"X-Api-Key": secret_key},
                )
                response.raise_for_status()
            payload = OfferwallGGApiResponse.model_validate(response.json())
        except httpx.TimeoutException as error:
            raise HTTPException(503, "Offerwall.GG offers are taking too long to load.") from error
        except httpx.HTTPStatusError as error:
            raise HTTPException(
                503,
                "Offerwall.GG could not return offers. Check the placement credentials and provider status.",
            ) from error
        except httpx.RequestError as error:
            raise HTTPException(503, "Offerwall.GG offers are temporarily unavailable.") from error
        except (ValueError, ValidationError) as error:
            raise HTTPException(502, "Offerwall.GG returned an invalid offer catalogue.") from error

        data = payload.data
        if not payload.success:
            raise HTTPException(502, "Offerwall.GG returned an unsuccessful offer catalogue.")
        if (
            data.currency.name.strip().upper() != settings.offerwall_gg_currency_name.strip().upper()
            or data.currency.name.strip().upper() != "USD"
            or data.currency.per_usd != Decimal("1")
        ):
            raise HTTPException(
                503,
                "Offerwall.GG placement must use USD currency at one unit per USD.",
            )

        offers: list[OfferwallGGOfferRead] = []
        for offer in data.offers:
            click_url = self._validated_click_url(
                offer.click_url,
                public_key,
                user.id,
                offer.id,
            )
            image_url = self._validated_image_url(offer.image)
            provider_payout = offer.reward / data.currency.per_usd
            user_reward = reward_decision_service.estimate_user_reward(
                db,
                user,
                OFFERWALL_GG_SLUG,
                offer.external_id,
                provider_payout,
            )
            offers.append(
                OfferwallGGOfferRead(
                    id=offer.id,
                    provider=offer.provider,
                    title=offer.name[:200],
                    description=offer.description[:1000],
                    requirements=offer.requirements[:2000],
                    image_url=image_url,
                    categories=offer.categories[:12],
                    devices=offer.devices[:8],
                    reward_usd=provider_payout,
                    user_reward_usd=user_reward,
                    reward_is_variable=offer.reward_is_variable,
                    reward_up_to=offer.reward_up_to,
                    payment_model=offer.payment_model,
                    featured=offer.featured,
                    click_url=click_url,
                )
            )

        return OfferwallGGOffersRead(
            offers=offers,
            page=data.pagination.page,
            pages=data.pagination.pages,
            total=data.pagination.total,
        )

    def _validated_click_url(
        self,
        value: str,
        public_key: str,
        user_id: str,
        offer_id: int,
    ) -> str:
        try:
            parsed = urlsplit(value)
            port = parsed.port
            query = parse_qs(parsed.query)
        except ValueError as error:
            raise HTTPException(502, "Offerwall.GG returned an unsafe offer link.") from error
        if (
            parsed.scheme != "https"
            or parsed.hostname != "offerwall.gg"
            or port is not None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path != f"/wall/{public_key}/click/{offer_id}"
            or query.get("userId") != [user_id]
        ):
            raise HTTPException(502, "Offerwall.GG returned an unsafe offer link.")
        return value

    def _validated_image_url(self, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError:
            return None
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or port is not None
            or parsed.username
            or parsed.password
        ):
            return None
        return value


offerwall_gg_catalog_service = OfferwallGGCatalogService()
