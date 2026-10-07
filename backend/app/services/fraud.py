from dataclasses import dataclass
@dataclass(frozen=True)
class FraudAssessment: score: int = 0; action: str = "ALLOW"
class FraudService:
    """Minimal, non-invasive hook; no automatic bans or reward decisions."""
    def assess_conversion(self, repeated: bool) -> FraudAssessment:
        return FraudAssessment(score=75, action="MANUAL_REVIEW") if repeated else FraudAssessment()
fraud_service = FraudService()
