"""Business logic for membership management and safety rules."""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.models.models import Membership, User, Organization


def count_org_admins(db: Session, org_id: int) -> int:
    """Return the number of admin members in an organization."""
    return (
        db.query(Membership)
        .filter(Membership.org_id == org_id, Membership.role == "admin")
        .count()
    )


def validate_not_last_admin(db: Session, org_id: int, target_user_id: int) -> None:
    """Ensure that modifying or removing target_user_id will not leave the org without an admin.
    
    Raises 409 Conflict if target is the last admin in the organization.
    """
    target_membership = (
        db.query(Membership)
        .filter(Membership.org_id == org_id, Membership.user_id == target_user_id)
        .first()
    )
    if not target_membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this organization"
        )

    if target_membership.role == "admin":
        admin_count = count_org_admins(db, org_id)
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot remove or demote the last remaining admin of the organization"
            )
