"""Authentication and Organization selection router."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend.app.db.session import get_db
from backend.app.models.models import User, Membership, Organization
from backend.app.core.security import (
    hash_password,
    verify_password,
    create_user_token,
    create_org_token
)
from backend.app.core.deps import get_current_user, get_token_payload
from backend.app.schemas.schemas import (
    UserRegister,
    UserLogin,
    LoginResponse,
    UserOut,
    OrgMembershipBrief,
    SelectOrgRequest,
    TokenResponse,
    UserMeResponse
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    """Create a new user account."""
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email address already exists"
        )

    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        password_hash=hash_password(user_in.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=LoginResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """Authenticate with email and password.
    
    Returns a user-scoped token along with the list of organizations the user belongs to.
    """
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch organizations with membership details
    memberships = (
        db.query(Membership, Organization.name)
        .join(Organization, Membership.org_id == Organization.id)
        .filter(Membership.user_id == user.id)
        .all()
    )

    org_list = [
        OrgMembershipBrief(org_id=m.Membership.org_id, org_name=m.name, role=m.Membership.role)
        for m in memberships
    ]

    user_token = create_user_token(user_id=user.id)
    return LoginResponse(
        access_token=user_token,
        token_type="bearer",
        user=user,
        organizations=org_list
    )


@router.post("/select-org", response_model=TokenResponse)
def select_org(
    payload_data: SelectOrgRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Switch or select active organization using a valid user token.
    
    Returns an organization-scoped token with claims (sub, org_id, role, type='org').
    """
    membership = (
        db.query(Membership)
        .filter(
            Membership.user_id == current_user.id,
            Membership.org_id == payload_data.org_id
        )
        .first()
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )

    org_token = create_org_token(
        user_id=current_user.id,
        org_id=membership.org_id,
        role=membership.role
    )

    return TokenResponse(
        access_token=org_token,
        token_type="bearer",
        org_id=membership.org_id,
        role=membership.role
    )
