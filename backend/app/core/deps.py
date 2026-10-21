"""FastAPI dependency injection utilities for authentication and tenant authorization.

Key dependencies:
- get_db: yields database session
- get_current_user: verifies user token (or org token) and returns the User record
- get_current_org_context: verifies org token, validates active membership row, returns (User, Membership)
- require_role(*allowed_roles): dependency factory enforcing that current org role is one of allowed_roles
"""
from typing import Optional, Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt

from backend.app.db.session import get_db
from backend.app.core.security import decode_token
from backend.app.models.models import User, Membership

security_scheme = HTTPBearer(auto_error=False)


def get_token_payload(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)) -> dict:
    """Extract and decode Bearer token."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(credentials.credentials)
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    payload: dict = Depends(get_token_payload),
    db: Session = Depends(get_db)
) -> User:
    """Validate token and resolve current active User."""
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject (sub) missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


class OrgContext:
    """Represents verified organization context for an authenticated request."""
    def __init__(self, user: User, membership: Membership, org_id: int, role: str):
        self.user = user
        self.membership = membership
        self.org_id = org_id
        self.role = role


def get_current_org_context(
    payload: dict = Depends(get_token_payload),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> OrgContext:
    """Validate org token and verify active membership row in the database.
    
    If membership has been revoked/deleted or modified, it takes effect immediately.
    """
    token_type = payload.get("type")
    if token_type != "org":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Organization-scoped token required for this action",
            headers={"WWW-Authenticate": "Bearer"},
        )

    org_id = payload.get("org_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Organization ID missing from token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Re-check membership row directly in the database
    membership = (
        db.query(Membership)
        .filter(Membership.user_id == user.id, Membership.org_id == org_id)
        .first()
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are no longer a member of this organization",
        )

    return OrgContext(user=user, membership=membership, org_id=org_id, role=membership.role)


def require_role(*allowed_roles: str) -> Callable[[OrgContext], OrgContext]:
    """Dependency factory that checks if the user's role in the active organization is authorized."""
    def role_checker(context: OrgContext = Depends(get_current_org_context)) -> OrgContext:
        if context.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action requires one of the following roles: {', '.join(allowed_roles)}"
            )
        return context

    return role_checker
