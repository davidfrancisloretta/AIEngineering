from datetime import datetime

from pydantic import BaseModel, field_validator


# -----------------------------------------------
# Campaign Metrics
# -----------------------------------------------
class MetricCreate(BaseModel):
    campaign_name: str
    impressions: int
    clicks: int
    views: int
    conversions: int

    @field_validator("impressions")
    @classmethod
    def impressions_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Impressions must be greater than zero")
        return v


class MetricUpdate(BaseModel):
    campaign_name: str | None = None
    impressions: int | None = None
    clicks: int | None = None
    views: int | None = None
    conversions: int | None = None

    @field_validator("impressions")
    @classmethod
    def impressions_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Impressions must be greater than zero")
        return v


class MetricResponse(BaseModel):
    id: int
    campaign_name: str
    impressions: int
    clicks: int
    views: int
    conversions: int
    ttr: float
    vtr: float
    cvr: float

    class Config:
        from_attributes = True


# -----------------------------------------------
# Auth
# -----------------------------------------------
class UserCreate(BaseModel):
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


# -----------------------------------------------
# Rave API Config
# -----------------------------------------------
class ApiKeyConfig(BaseModel):
    rave_public_key: str
    rave_secret_key: str


class ApiKeyResponse(BaseModel):
    rave_public_key: str
    updated_at: datetime

    class Config:
        from_attributes = True


# -----------------------------------------------
# Rave Transactions
# -----------------------------------------------
class RaveTransactionResponse(BaseModel):
    id: int
    rave_id: int | None
    transaction_ref: str | None
    amount: float | None
    currency: str | None
    status: str | None
    payment_type: str | None
    customer_email: str | None
    customer_name: str | None
    fetched_at: datetime

    class Config:
        from_attributes = True
