from __future__ import annotations

import logging
from decimal import Decimal
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import PayoutSettings, User
from app.schemas.timewall_surveys import (
    TimeWallApiResponse,
    TimeWallSurveyRead,
    TimeWallSurveysRead,
)
from app.services.rewards import reward_decision_service

TIMEWALL_SURVEYS_API_URL = "https://api.timewall.io/get-surveys"
logger = logging.getLogger(__name__)


class TimeWallSurveyCatalogService:
    async def list_surveys(
        self,
        db: Session,
        user: User,
        user_ip: str,
        user_agent: str,
    ) -> TimeWallSurveysRead:
        if not settings.timewall_enabled:
            raise HTTPException(404, "TimeWall is not enabled.")

        api_key = (settings.timewall_api_key or "").strip()
        if not api_key:
            raise HTTPException(503, "TimeWall API key is not configured.")
        if not user_ip:
            raise HTTPException(503, "A verified user IP is required to load TimeWall surveys.")
        if not user_agent.strip():
            raise HTTPException(503, "A user agent is required to load TimeWall surveys.")

        request_body = {
            "uid": user.id,
            "ip": user_ip,
            "user_agent": user_agent[:512],
            "limit": 10,
            "provider": "all",
        }

        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=False) as client:
                response = await client.post(
                    TIMEWALL_SURVEYS_API_URL,
                    json=request_body,
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                response.raise_for_status()
            payload = TimeWallApiResponse.model_validate(response.json())
        except httpx.TimeoutException as error:
            raise HTTPException(503, "TimeWall surveys are taking too long to load.") from error
        except httpx.HTTPStatusError as error:
            logger.warning(
                "TimeWall survey catalogue request failed with HTTP status %s.",
                error.response.status_code,
            )
            raise HTTPException(503, "TimeWall surveys are temporarily unavailable.") from error
        except httpx.RequestError as error:
            raise HTTPException(503, "TimeWall surveys are temporarily unavailable.") from error
        except (ValueError, ValidationError) as error:
            raise HTTPException(502, "TimeWall returned an invalid survey catalogue.") from error

        if not payload.success:
            raise HTTPException(503, "TimeWall could not return surveys.")

        valid_surveys = [
            survey for survey in payload.surveys if self._is_safe_survey_link(survey.link)
        ]
        if len(valid_surveys) != len(payload.surveys):
            raise HTTPException(502, "TimeWall returned an unsafe survey link.")

        estimated_rewards = reward_decision_service.estimate_user_rewards_for_offers(
            db,
            user,
            "timewall",
            [(survey.id, survey.usd_rate) for survey in valid_surveys],
        )
        surveys = [
            TimeWallSurveyRead(
                id=survey.id,
                title=f"Survey #{survey.id}",
                estimated_time_minutes=survey.loi,
                provider_currency_amount=survey.currency_amount,
                provider_currency=payload.currency,
                estimated_user_reward_usd=estimated_reward,
                entry_url=survey.link,
            )
            for survey, estimated_reward in zip(valid_surveys, estimated_rewards, strict=True)
        ]
        payout_settings = db.get(PayoutSettings, "default")
        return TimeWallSurveysRead(
            surveys=surveys,
            total=len(surveys),
            currency=payload.currency,
            usd_bdt_rate=payout_settings.usd_bdt_rate if payout_settings else None,
        )

    @staticmethod
    def _is_safe_survey_link(value: str) -> bool:
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError:
            return False
        return (
            parsed.scheme == "https"
            and parsed.hostname == "timesurveys.com"
            and parsed.path.startswith("/s/")
            and port is None
            and parsed.username is None
            and parsed.password is None
            and not parsed.fragment
        )


timewall_survey_catalog_service = TimeWallSurveyCatalogService()
