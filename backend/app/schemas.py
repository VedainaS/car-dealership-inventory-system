from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import UserRole

BCRYPT_MAX_PASSWORD_BYTES = 72


def _reject_password_over_bcrypt_limit(value: str) -> str:
    if len(value.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password must be at most {BCRYPT_MAX_PASSWORD_BYTES} bytes when UTF-8 encoded."
        )
    return value


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_within_bcrypt_limit(cls, value: str) -> str:
        return _reject_password_over_bcrypt_limit(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("password")
    @classmethod
    def password_within_bcrypt_limit(cls, value: str) -> str:
        return _reject_password_over_bcrypt_limit(value)


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Vehicle schemas
# ---------------------------------------------------------------------------


class VehicleCreate(BaseModel):
    """Payload for POST /api/vehicles (admin only).

    price    – must be strictly positive (> 0).
    quantity – non-negative integer; 0 is allowed (pre-listing before delivery).
    """

    make: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0, description="Sale price in USD; must be > 0")
    quantity: int = Field(ge=0, description="Units in stock; 0 = out of stock")


class VehicleUpdate(BaseModel):
    """Payload for PUT /api/vehicles/{id} (admin only).

    All fields are required (full replacement, not partial patch).
    """

    make: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0, description="Sale price in USD; must be > 0")
    quantity: int = Field(ge=0, description="Units in stock; 0 = out of stock")


class VehiclePublic(BaseModel):
    """Response schema for vehicle endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    make: str
    model: str
    category: str
    price: float
    quantity: int


class RestockRequest(BaseModel):
    """Payload for POST /api/vehicles/{id}/restock (admin only).

    amount – must be a positive integer (> 0); validated at schema level
    so invalid values return 422 Unprocessable Entity before reaching the
    service layer.
    """

    amount: int = Field(gt=0, description="Number of units to add to stock; must be > 0")
