"""Password hashing and JWT generation/verification utilities.

Flow as per TRD:
1. User Token:
   - Claims: sub (user_id), type="user", exp
2. Org Token:
   - Claims: sub (user_id), org_id, role, type="org", exp
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import bcrypt
import jwt
from backend.app.core.config import settings


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_user_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """Create a user-scoped JWT token (after initial login)."""
    return create_access_token(
        data={"sub": str(user_id), "type": "user"},
        expires_delta=expires_delta
    )


def create_org_token(user_id: int, org_id: int, role: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create an organization-scoped JWT token (after selecting an organization)."""
    return create_access_token(
        data={
            "sub": str(user_id),
            "org_id": org_id,
            "role": role,
            "type": "org"
        },
        expires_delta=expires_delta
    )


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token, raising jwt.PyJWTError on failure."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
