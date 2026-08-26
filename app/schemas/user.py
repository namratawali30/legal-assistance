from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


MAX_BCRYPT_PASSWORD_BYTES = 72


def validate_password_length(
    password: str,
) -> str:
    if (
        len(
            password.encode(
                "utf-8"
            )
        )
        > MAX_BCRYPT_PASSWORD_BYTES
    ):
        raise ValueError(
            "Password must not exceed "
            "72 UTF-8 bytes."
        )

    return password


class UserBase(BaseModel):
    email: EmailStr

    full_name: str = Field(
        min_length=3,
        max_length=100,
    )

    model_config = ConfigDict(
        extra="forbid",
    )

    @field_validator(
        "full_name"
    )
    @classmethod
    def normalize_full_name(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if len(value) < 3:
            raise ValueError(
                "Full name must contain "
                "at least 3 characters."
            )

        return value


class UserCreate(
    UserBase
):
    password: str = Field(
        min_length=8,
        max_length=128,
    )

    @field_validator(
        "password"
    )
    @classmethod
    def validate_password(
        cls,
        password: str,
    ) -> str:
        return validate_password_length(
            password
        )


class UserLogin(BaseModel):
    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    model_config = ConfigDict(
        extra="forbid",
    )

    @field_validator(
        "password"
    )
    @classmethod
    def validate_password(
        cls,
        password: str,
    ) -> str:
        return validate_password_length(
            password
        )


class TokenResponse(BaseModel):
    access_token: str

    token_type: str = "bearer"


class UserResponse(
    UserBase
):
    id: str

    role: str

    is_active: bool

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )