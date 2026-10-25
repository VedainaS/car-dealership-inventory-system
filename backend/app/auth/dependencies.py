"""FastAPI dependency callables for authentication and authorisation.

Usage
-----
    from app.auth.dependencies import get_current_user, require_admin

    @router.get("/protected")
    def protected_route(user: User = Depends(get_current_user)):
        ...

    @router.post("/admin-only")
    def admin_route(_admin: User = Depends(require_admin)):
        ...

JWT verification
----------------
The token is decoded using the configured secret and algorithm.
python-jose raises JWTError for any of the following conditions, all of
which result in 401 Unauthorized:

  - Invalid signature
  - Expired token (exp claim in the past)
  - Malformed / missing claims

After successful decoding the user is loaded from the database by the
integer ``sub`` claim.  A missing user (e.g. after account deletion) also
returns 401 so callers cannot infer whether the account exists.

Admin enforcement
-----------------
``require_admin`` is a thin dependency that wraps ``get_current_user`` and
raises 403 Forbidden if the loaded user's role is not ADMIN.  The role check
is performed server-side against the database row, not against the JWT
payload, so a demoted user cannot retain privileges by replaying an old token.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Optional
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User, UserRole

# auto_error=False prevents FastAPI from returning 403 when the header is
# absent; we raise our own 401 _CREDENTIALS_EXCEPTION instead.
_bearer = HTTPBearer(auto_error=False)

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired token.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Decode the JWT, verify signature + expiry, and load the user from the DB.

    Raises 401 for any of: missing header, invalid/expired token, deleted user.
    """
    if credentials is None:
        raise _CREDENTIALS_EXCEPTION
    settings = get_settings()
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        sub: str | None = payload.get("sub")
        if sub is None:
            raise JWTError("missing sub claim")
        user_id = int(sub)
    except (JWTError, ValueError):
        raise _CREDENTIALS_EXCEPTION

    user = db.get(User, user_id)
    if user is None:
        raise _CREDENTIALS_EXCEPTION
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Extend get_current_user by additionally requiring the ADMIN role.

    Raises 403 Forbidden if the authenticated user is not an admin.
    The role is read from the database row, not from the JWT payload.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )
    return current_user
