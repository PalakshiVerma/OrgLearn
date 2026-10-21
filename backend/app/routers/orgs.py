"""User profile and organizations management router."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.models import User, Organization, Membership
from backend.app.core.deps import get_current_user, get_token_payload
from backend.app.schemas.schemas import (
    UserMeResponse,
    OrgMembershipBrief,
    OrgCreate,
    OrgOut
)

router = APIRouter(tags=["users & organizations"])


@router.get("/me", response_model=UserMeResponse)
def get_me(
    payload: dict = Depends(get_token_payload),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve details of the currently authenticated user, their org memberships, and active org if in org-scope."""
    memberships = (
        db.query(Membership, Organization.name)
        .join(Organization, Membership.org_id == Organization.id)
        .filter(Membership.user_id == current_user.id)
        .all()
    )

    org_list = [
        OrgMembershipBrief(org_id=m.Membership.org_id, org_name=m.name, role=m.Membership.role)
        for m in memberships
    ]

    active_org = None
    if payload.get("type") == "org":
        active_org_id = payload.get("org_id")
        for org in org_list:
            if org.org_id == active_org_id:
                active_org = org
                break

    return UserMeResponse(
        user=current_user,
        organizations=org_list,
        active_org=active_org
    )


@router.post("/orgs", response_model=OrgOut, status_code=status.HTTP_201_CREATED)
def create_organization(
    org_in: OrgCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new organization. The creator is automatically added as an admin member."""
    org = Organization(
        name=org_in.name,
        created_by=current_user.id
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    # Assign creator as admin
    membership = Membership(
        user_id=current_user.id,
        org_id=org.id,
        role="admin"
    )
    db.add(membership)
    db.commit()

    return org


@router.get("/orgs", response_model=List[OrgMembershipBrief])
def list_my_organizations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all organizations that the current user belongs to."""
    memberships = (
        db.query(Membership, Organization.name)
        .join(Organization, Membership.org_id == Organization.id)
        .filter(Membership.user_id == current_user.id)
        .all()
    )

    return [
        OrgMembershipBrief(org_id=m.Membership.org_id, org_name=m.name, role=m.Membership.role)
        for m in memberships
    ]
