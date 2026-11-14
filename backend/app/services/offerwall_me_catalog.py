from __future__ import annotations

import logging
import re
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.offer_providers.offerwall_me import (
    OFFERWALL_ME_SLUG,
    OfferwallMeConfigurationError,
    offerwall_me_adapter,
)
from app.models import PayoutSettings, User
from app.schemas.offerwall_me import (
    OfferwallMeApiOffer,
    OfferwallMeApiResponse,
    OfferwallMeOfferRead,
    OfferwallMeOffersRead,
)
from app.services.rewards import reward_decision_service

API_OFFERS_URL = "https://offerwall.me/offerapi.php"
COUNTRY_PATTERN = re.compile(r"^[A-Z]{2}$")
logger = logging.getLogger(__name__)


class OfferwallMeCatalogService:
    async def list_offers(
        self,
        db: Session,
        user: User,
        user_ip: str,
        user_country: str,
        user_agent: str,
    ) -> OfferwallMeOffersRead:
        if not settings.offerwall_me_enabled:
            raise HTTPException(404, "Offerwall.me is not enabled.")
        if not user_ip:
            raise HTTPException(503, "A verified user IP is required for Offerwall.me offers.")
        user_country = user_country.strip().upper()
        if not COUNTRY_PATTERN.fullmatch(user_country):
            raise HTTPException(503, "A valid user country is required for Offerwall.me offers.")

        try:
            public_api_key, _, api_token = offerwall_me_adapter.api_credentials()
            identity_expires, identity_signature = offerwall_me_adapter.signed_user_identity(
                user.id
            )
        except OfferwallMeConfigurationError as error:
            raise HTTPException(503, str(error)) from error

        params = {
            "api": public_api_key,
            "id": user.id,
            "ip": user_ip,
            "token": api_token,
            "country": user_country,
            "identityExpires": identity_expires,
            "identitySignature": identity_signature,
        }
        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=False) as client:
                response = await client.get(
                    API_OFFERS_URL,
                    params=params,
                    headers={"User-Agent": user_agent[:512]} if user_agent else {},
                )
            if response.status_code == 404:
                return OfferwallMeOffersRead(offers=[], total=0)
            response.raise_for_status()
            payload = OfferwallMeApiResponse.model_validate(response.json())
        except httpx.TimeoutException as error:
            raise HTTPException(503, "Offerwall.me offers are taking too long to load.") from error
        except httpx.HTTPStatusError as error:
            logger.warning(
                "Offerwall.me catalogue request failed with HTTP status %s.",
                error.response.status_code,
            )
            raise HTTPException(
                503,
                "Offerwall.me could not return offers. Check its placement credentials and provider status.",
            ) from error
        except httpx.RequestError as error:
            raise HTTPException(503, "Offerwall.me offers are temporarily unavailable.") from error
        except (ValueError, ValidationError) as error:
            raise HTTPException(502, "Offerwall.me returned an invalid offer catalogue.") from error

        if payload.status == 404:
            return OfferwallMeOffersRead(offers=[], total=0)
        if payload.status != 200:
            raise HTTPException(503, "Offerwall.me could not return offers.")

        target_country = user_country
        eligible_offers: list[tuple[OfferwallMeApiOffer, str, Decimal]] = []
        for offer in payload.data or []:
            eligible_countries = {country.strip().upper() for country in offer.countries}
            if (
                eligible_countries
                and "ALL" not in eligible_countries
                and target_country not in eligible_countries
            ):
                continue
            click_url = self._validated_click_url(offer.url, user.id)
            if not offer.reward.is_finite() or offer.reward <= 0:
                continue
            payout_usd = (
                offer.reward / settings.offerwall_me_exchange_rate
            ).quantize(Decimal("0.00000001"))
            eligible_offers.append((offer, click_url, payout_usd))

        user_rewards = reward_decision_service.estimate_user_rewards_for_offers(
            db,
            user,
            OFFERWALL_ME_SLUG,
            [(offer.id, payout_usd) for offer, _, payout_usd in eligible_offers],
        )
        offers = [
            OfferwallMeOfferRead(
                id=offer.id,
                provider=offer.provider[:80],
                title=(offer.title or offer.name or "Offerwall.me offer")[:200],
                description=offer.description[:1000],
                image_url=self._validated_image_url(offer.image),
                devices=[item[:40] for item in offer.devices[:8]],
                countries=[
                    item.upper() if item.upper() == "ALL" else item.upper()[:2]
                    for item in offer.countries[:40]
                ],
                provider_reward=offer.reward,
                reward_name=settings.offerwall_me_currency_name,
                provider_payout_usd=payout_usd,
                estimated_user_reward_usd=user_reward,
                multi_step=offer.is_multi_step,
                click_url=click_url,
            )
            for (offer, click_url, payout_usd), user_reward in zip(
                eligible_offers, user_rewards
            )
        ]

        payout_settings = db.get(PayoutSettings, "default")
        return OfferwallMeOffersRead(
            offers=offers,
            total=len(offers),
            usd_bdt_rate=payout_settings.usd_bdt_rate if payout_settings else None,
        )

    @staticmethod
    def _validated_click_url(value: str, user_id: str) -> str:
        try:
            parsed = urlsplit(value)
            port = parsed.port
            query = parse_qs(parsed.query)
        except ValueError as error:
            raise HTTPException(502, "Offerwall.me returned an unsafe offer link.") from error
        if (
            parsed.scheme != "https"
            or parsed.hostname != "offerwall.me"
            or port is not None
            or parsed.username is not None
            or parsed.password is not None
            or query.get("id") != [user_id]
        ):
            raise HTTPException(502, "Offerwall.me returned an unsafe offer link.")
        return value

    @staticmethod
    def _validated_image_url(value: str | None) -> str | None:
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


offerwall_me_catalog_service = OfferwallMeCatalogService()
