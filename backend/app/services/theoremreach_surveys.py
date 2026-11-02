from __future__ import annotations

from urllib.parse import urlencode
from uuid import uuid4

import httpx
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.offer_providers.theoremreach import (
    THEOREMREACH_SLUG,
    TheoremReachConfigurationError,
    theoremreach_adapter,
)
from app.models import User
from app.schemas.theoremreach_surveys import (
    TheoremReachSurveyApiResponse,
    TheoremReachSurveyRead,
    TheoremReachSurveysRead,
)
from app.services.rewards import reward_decision_service

THEOREMREACH_SURVEYS_API_URL = "https://api.theoremreach.com/api/publishers/v1/surveys"


class TheoremReachSurveyCatalogService:
    async def list_surveys(
        self,
        db: Session,
        user: User,
        user_ip: str,
    ) -> TheoremReachSurveysRead:
        if not settings.theoremreach_enabled:
            raise HTTPException(404, "TheoremReach is not enabled.")
        if not settings.theoremreach_surveys_api_enabled:
            raise HTTPException(404, "TheoremReach Surveys API is not enabled.")

        try:
            api_key, _, partner_id, _ = theoremreach_adapter.publisher_api_credentials()
        except TheoremReachConfigurationError as error:
            raise HTTPException(503, str(error)) from error
        if not partner_id:
            raise HTTPException(503, "TheoremReach partner ID is required for survey cards.")

        params = [
            ("api_key", api_key),
            ("user_id", user.id),
            ("ip", user_ip),
            ("country_code", user.country.upper()),
            ("max_result_count", "100"),
        ]
        unsigned_url = f"{THEOREMREACH_SURVEYS_API_URL}?{urlencode(params)}"
        signed_url = (
            f"{unsigned_url}&hash="
            f"{theoremreach_adapter.sign_publisher_api_request(unsigned_url)}"
        )

        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=False) as client:
                response = await client.get(signed_url)
                response.raise_for_status()
            payload = TheoremReachSurveyApiResponse.model_validate(response.json())
        except httpx.TimeoutException as error:
            raise HTTPException(503, "TheoremReach surveys are taking too long to load.") from error
        except httpx.HTTPStatusError as error:
            if error.response.status_code in {401, 403}:
                raise HTTPException(
                    503,
                    "TheoremReach Publisher API access must be enabled by your account manager.",
                ) from error
            raise HTTPException(503, "TheoremReach surveys are temporarily unavailable.") from error
        except httpx.RequestError as error:
            raise HTTPException(503, "TheoremReach surveys are temporarily unavailable.") from error
        except (ValueError, ValidationError) as error:
            raise HTTPException(502, "TheoremReach returned an invalid survey catalogue.") from error

        surveys: list[TheoremReachSurveyRead] = []
        for survey in payload.surveys:
            try:
                entry_url = theoremreach_adapter.sign_survey_entry_link(
                    survey.entry_link,
                    user.id,
                    survey.campaign_id,
                    uuid4().hex,
                )
            except TheoremReachConfigurationError as error:
                raise HTTPException(502, str(error)) from error
            user_reward = reward_decision_service.estimate_user_reward(
                db,
                user,
                THEOREMREACH_SLUG,
                str(survey.campaign_id),
                survey.cpi,
            )
            surveys.append(
                TheoremReachSurveyRead(
                    id=f"{survey.campaign_id}:{survey.quota_id or ','.join(map(str, survey.quota_ids))}",
                    survey_id=survey.campaign_id,
                    title=f"Survey #{survey.campaign_id}",
                    rank=survey.rank,
                    estimated_time_minutes=survey.loi,
                    incidence=survey.incidence,
                    user_reward_usd=user_reward,
                    entry_url=entry_url,
                )
            )

        return TheoremReachSurveysRead(surveys=surveys)


theoremreach_survey_catalog_service = TheoremReachSurveyCatalogService()
