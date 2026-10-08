from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    confirm_password: str
    country: str = Field(min_length=2, max_length=2)
    referral_code: str | None = Field(default=None, max_length=20)
    terms_accepted: bool
    @field_validator("country")
    @classmethod
    def country_code(cls, value: str) -> str:
        if not value.isalpha(): raise ValueError("country must be an ISO alpha-2 code")
        return value.upper()
    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        if not any(c.islower() for c in value) or not any(c.isupper() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError("password must contain upper, lower, and numeric characters")
        return value
    @model_validator(mode="after")
    def matches_and_terms(self):
        if self.password != self.confirm_password: raise ValueError("passwords do not match")
        if not self.terms_accepted: raise ValueError("terms must be accepted")
        return self

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class TokenRequest(BaseModel): token: str = Field(min_length=20, max_length=512)
class EmailRequest(BaseModel): email: EmailStr
class ResetPasswordRequest(TokenRequest):
    password: str = Field(min_length=12, max_length=128)
    confirm_password: str

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        if not any(c.islower() for c in value) or not any(c.isupper() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError("password must contain upper, lower, and numeric characters")
        return value

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password: raise ValueError("passwords do not match")
        return self

class UserResponse(BaseModel):
    id: str; email: EmailStr; full_name: str; country: str; status: str; email_verified: bool; roles: list[str]
class WalletResponse(BaseModel):
    available_balance: str; pending_balance: str; lifetime_earned: str; lifetime_withdrawn: str; currency: str
