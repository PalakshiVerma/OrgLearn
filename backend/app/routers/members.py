"""Organization members management router (Admin only)."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.models import User, Membership
from backend.app.core.deps import require_role, OrgContext
from backend.app.schemas.schemas import (
    MemberAdd,
    MemberUpdateRole,
    MemberOut
)
from backend.app.services.members import validate_not_last_admin

router = APIRouter(prefix="/members", tags=["members"])


@router.get("", response_model=List[MemberOut])
def list_members(
    context: OrgContext = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """List all members of the active organization (Admin only)."""
    memberships = (
        db.query(Membership, User.email, User.full_name)
        .join(User, Membership.user_id == User.id)
        .filter(Membership.org_id == context.org_id)
        .all()
    )

    return [
        MemberOut(
            user_id=m.Membership.user_id,
            email=m.email,
            full_name=m.full_name,
            role=m.Membership.role,
            created_at=m.Membership.created_at
        )
        for m in memberships
    ]


@router.post("", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def add_member(
    member_in: MemberAdd,
    context: OrgContext = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Add an existing user to the active organization by their registered email (Admin only)."""
    user = db.query(User).filter(User.email == member_in.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email does not exist"
        )

    existing_membership = (
        db.query(Membership)
        .filter(Membership.org_id == context.org_id, Membership.user_id == user.id)
        .first()
    )
    if existing_membership:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this organization"
        )

    membership = Membership(
        user_id=user.id,
        org_id=context.org_id,
        role=member_in.role
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)

    return MemberOut(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=membership.role,
        created_at=membership.created_at
    )


@router.patch("/{user_id}", response_model=MemberOut)
def update_member_role(
    user_id: int,
    role_in: MemberUpdateRole,
    context: OrgContext = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Change a member's role in the active organization (Admin only).
    
    Protects the last remaining admin from being demoted.
    """
    membership = (
        db.query(Membership)
        .filter(Membership.org_id == context.org_id, Membership.user_id == user_id)
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this organization"
        )

    # If demoting an admin, verify they are not the last admin
    if membership.role == "admin" and role_in.role != "admin":
        validate_not_last_admin(db, context.org_id, user_id)

    membership.role = role_in.role
    db.commit()
    db.refresh(membership)

    user = db.query(User).filter(User.id == user_id).first()
    return MemberOut(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=membership.role,
        created_at=membership.created_at
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    user_id: int,
    context: OrgContext = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Remove a member from the active organization (Admin only).
    
    Protects the last remaining admin from being removed.
    """
    membership = (
        db.query(Membership)
        .filter(Membership.org_id == context.org_id, Membership.user_id == user_id)
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this organization"
        )

    if membership.role == "admin":
        validate_not_last_admin(db, context.org_id, user_id)

    db.delete(membership)
    db.commit()
    return None
