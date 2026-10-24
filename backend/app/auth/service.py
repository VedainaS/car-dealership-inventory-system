from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.auth.password import hash_password, verify_password
from app.models import User, UserRole
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserPublic


class DuplicateEmailError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


def register_user(db: Session, payload: RegisterRequest) -> UserPublic:
    normalized_email = payload.email.lower()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing is not None:
        raise DuplicateEmailError

    user = User(
        email=normalized_email,
        hashed_password=hash_password(payload.password),
        role=UserRole.USER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserPublic.model_validate(user)


def login_user(db: Session, payload: LoginRequest) -> TokenResponse:
    normalized_email = payload.email.lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise InvalidCredentialsError

    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)
