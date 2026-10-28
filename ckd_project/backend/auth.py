
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models import User


_passwords = PasswordHash.recommended()
_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash a password using the application's configured password hasher."""
    return _passwords.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    """Verify a password against its stored hash."""
    try:
        return _passwords.verify(password, encoded)
    except Exception:
        return False


def create_token(user: User) -> str:
    """Create a JWT access token for the given user."""
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user.user_id),
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm="HS256",
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Resolve and authorize the current user from the bearer token."""
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Sign in required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"],
        )
        user_id = int(payload.get("sub", "0"))
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token",
        )

    user = db.get(User, user_id)

    if not user or user.account_status != "APPROVED":
        raise HTTPException(
            status_code=403,
            detail="Account is not approved or is suspended",
        )

    return user


def require_roles(*roles: str):
    """Restrict an endpoint to users with one of the specified roles."""

    def checker(
        user: User = Depends(get_current_user),
    ) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to perform this action",
            )
        return user

    return checker


def ensure_user_can_access(patient_id: str, user: User) -> bool:
    """
    Preserve the existing workspace-level access behavior.

    The starter project does not implement doctor-patient assignments.
    """
    return True
