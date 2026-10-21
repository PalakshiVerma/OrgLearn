"""Course-related business logic and permission enforcement."""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.models.models import Course
from backend.app.core.deps import OrgContext


def get_course_or_404(db: Session, course_id: int, org_id: int) -> Course:
    """Retrieve a course by ID ensuring it belongs to the active organization.
    
    Returns 404 if not found or if the course belongs to another organization
    (preventing cross-org data enumeration).
    """
    course = (
        db.query(Course)
        .filter(Course.id == course_id, Course.org_id == org_id)
        .first()
    )
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    return course


def verify_course_write_permission(course: Course, context: OrgContext) -> None:
    """Verify that the current user has permission to modify or delete the course.
    
    Admins can modify/delete any course in their org.
    Instructors can only modify/delete courses they created.
    Learners cannot modify courses (403).
    """
    if context.role == "admin":
        return
    if context.role == "instructor" and course.created_by == context.user.id:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to modify this course"
    )
