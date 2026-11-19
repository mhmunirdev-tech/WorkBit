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
from app.models import PayoutSettings, User
from app.schemas.moonetix import (
    MoonetixApiOffer,
    MoonetixApiResponse,
    MoonetixGoalRead,
    MoonetixOfferRead,
    MoonetixOffersRead,
)
from app.services.rewards import reward_decision_service

MOONETIX_OFFERS_API_URL = "https://api.moonetix.com/v1/offers"
COUNTRY_PATTERN = re.compile(r"^[A-Z]{2}$")
logger = logging.getLogger(__name__)


class MoonetixCatalogService:
    async def list_offers(
        self,
        db: Session,
        user: User,
        user_country: str,
        user_agent: str,
    ) -> MoonetixOffersRead:
        if not settings.moonetix_enabled:
            raise HTTPException(404, "Moonetix is not enabled.")

        app_id = (settings.moonetix_app_id or "").strip()
        api_key = (settings.moonetix_api_key or "").strip()
        currency = settings.moonetix_currency_name.strip()
        if not app_id or not api_key:
            raise HTTPException(503, "Moonetix API credentials are not configured.")
        if not currency or len(currency) > 16:
            raise HTTPException(503, "Moonetix reward currency is invalid.")

        country = user_country.strip().upper()
        if not COUNTRY_PATTERN.fullmatch(country):
            raise HTTPException(503, "A valid user country is required for Moonetix offers.")

        params = {"user_id": user.id, "country": country}
        if user_agent:
            params["ua"] = user_agent[:512]
        else:
            params["device"] = "desktop"

        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=False) as client:
                response = await client.get(
                    MOONETIX_OFFERS_API_URL,
                    params=params,
                    headers={"Authorization": f"Bearer {api_key}"},
                )
            if response.status_code == 403:
                try:
                    error_payload = response.json()
                except ValueError:
                    error_payload = {}
                if (
                    isinstance(error_payload, dict)
                    and error_payload.get("error") == "user_blocked"
                ):
                    return self._empty_result(db, currency)
            response.raise_for_status()
            payload = MoonetixApiResponse.model_validate(response.json())
        except httpx.TimeoutException as error:
            raise HTTPException(503, "Moonetix offers are taking too long to load.") from error
        except httpx.HTTPStatusError as error:
            logger.warning(
                "Moonetix catalogue request failed with HTTP status %s.",
                error.response.status_code,
            )
            raise HTTPException(
                503,
                "Moonetix could not return offers. Check its API key and app status.",
            ) from error
        except httpx.RequestError as error:
            raise HTTPException(503, "Moonetix offers are temporarily unavailable.") from error
        except (ValueError, ValidationError) as error:
            raise HTTPException(502, "Moonetix returned an invalid offer catalogue.") from error

        if not payload.ok:
            if payload.error == "user_blocked":
                return self._empty_result(db, currency)
            logger.warning("Moonetix catalogue returned provider error code %s.", payload.error)
            raise HTTPException(503, "Moonetix could not return offers.")
        if payload.currency.strip().casefold() != currency.casefold():
            raise HTTPException(
                503,
                "Moonetix offer currency does not match the configured currency.",
            )

        valid_offers: list[tuple[MoonetixApiOffer, str, Decimal | None]] = []
        for offer in payload.offers:
            if offer.payout_usd <= 0 or offer.reward <= 0:
                continue
            start_url = self._validated_start_url(offer.start_url, app_id, user.id)
            valid_offers.append((offer, start_url, offer.payout_max_usd))

        payout_entries: list[tuple[str, Decimal]] = []
        for offer, _, max_payout in valid_offers:
            payout_entries.append((str(offer.id), offer.payout_usd))
            if max_payout is not None and max_payout > offer.payout_usd:
                payout_entries.append((str(offer.id), max_payout))
            else:
                payout_entries.append((str(offer.id), offer.payout_usd))

        estimated_rewards = reward_decision_service.estimate_user_rewards_for_offers(
            db,
            user,
            "moonetix",
            payout_entries,
        )

        offers: list[MoonetixOfferRead] = []
        reward_index = 0
        for offer, start_url, max_payout in valid_offers:
            min_reward = estimated_rewards[reward_index]
            max_reward = estimated_rewards[reward_index + 1]
            reward_index += 2
            has_higher_maximum = (
                max_payout is not None and max_payout > offer.payout_usd
            )
            offers.append(
                MoonetixOfferRead(
                    id=str(offer.id),
                    title=offer.title[:200],
                    category=offer.category[:40],
                    description=offer.description[:2000],
                    goals=[
                        MoonetixGoalRead(
                            name=goal.name[:200],
                            reward=goal.reward,
                            payout_usd=goal.payout_usd,
                        )
                        for goal in offer.goals[:30]
                    ],
                    reward=offer.reward,
                    reward_max=offer.reward_max,
                    reward_name=currency,
                    payout_usd=offer.payout_usd,
                    estimated_user_reward_usd=min_reward,
                    estimated_user_reward_max_usd=(
                        max_reward if has_higher_maximum else None
                    ),
                    is_variable=offer.payout_type.casefold() == "revshare" and has_higher_maximum,
                    image_url=self._validated_image_url(offer.thumbnail_url),
                    start_url=start_url,
                )
            )

        payout_settings = db.get(PayoutSettings, "default")
        return MoonetixOffersRead(
            offers=offers,
            total=len(offers),
            currency=payload.currency,
            usd_bdt_rate=payout_settings.usd_bdt_rate if payout_settings else None,
            history_url=self._validated_history_url(payload.history_url, app_id, user.id),
        )

    @staticmethod
    def _empty_result(db: Session, currency: str) -> MoonetixOffersRead:
        payout_settings = db.get(PayoutSettings, "default")
        return MoonetixOffersRead(
            offers=[],
            total=0,
            currency=currency,
            usd_bdt_rate=payout_settings.usd_bdt_rate if payout_settings else None,
        )

    @staticmethod
    def _validated_start_url(value: str, app_id: str, user_id: str) -> str:
        try:
            parsed = urlsplit(value)
            port = parsed.port
            query = parse_qs(parsed.query)
        except ValueError as error:
            raise HTTPException(502, "Moonetix returned an unsafe offer link.") from error
        if (
            parsed.scheme != "https"
            or parsed.hostname != "wall.moonetix.com"
            or port is not None
            or parsed.username is not None
            or parsed.password is not None
            or not parsed.path.startswith(f"/{app_id}/offer/")
            or query.get("user_id") != [user_id]
            or len(query.get("hash", [])) != 1
        ):
            raise HTTPException(502, "Moonetix returned an unsafe offer link.")
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

    @staticmethod
    def _validated_history_url(value: str | None, app_id: str, user_id: str) -> str | None:
        if value is None:
            return None
        try:
            parsed = urlsplit(value)
            port = parsed.port
            query = parse_qs(parsed.query)
        except ValueError:
            return None
        if (
            parsed.scheme != "https"
            or parsed.hostname != "wall.moonetix.com"
            or port is not None
            or parsed.username
            or parsed.password
            or parsed.path != f"/{app_id}"
            or query.get("user_id") != [user_id]
            or len(query.get("hash", [])) != 1
        ):
            return None
        return value


moonetix_catalog_service = MoonetixCatalogService()
