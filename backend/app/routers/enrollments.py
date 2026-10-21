"""Enrollments, lesson completion, and learning progress router."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.models import Course, Lesson, Enrollment, LessonProgress, User
from backend.app.core.deps import get_current_org_context, require_role, OrgContext
from backend.app.schemas.schemas import (
    EnrollmentOut,
    MyLearningCourse
)
from backend.app.services.courses import get_course_or_404, verify_course_write_permission

router = APIRouter(tags=["enrollments & learning"])


@router.post("/courses/{course_id}/enroll", response_model=EnrollmentOut, status_code=status.HTTP_201_CREATED)
def enroll_in_course(
    course_id: int,
    context: OrgContext = Depends(get_current_org_context),
    db: Session = Depends(get_db)
):
    """Enroll the current user in a course within the active organization."""
    course = get_course_or_404(db, course_id, context.org_id)

    # Check if already enrolled
    existing = (
        db.query(Enrollment)
        .filter(
            Enrollment.user_id == context.user.id,
            Enrollment.course_id == course.id,
            Enrollment.org_id == context.org_id
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already enrolled in this course"
        )

    enrollment = Enrollment(
        user_id=context.user.id,
        course_id=course.id,
        org_id=context.org_id
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    return EnrollmentOut(
        id=enrollment.id,
        user_id=enrollment.user_id,
        course_id=enrollment.course_id,
        org_id=enrollment.org_id,
        enrolled_at=enrollment.enrolled_at,
        user_name=context.user.full_name,
        user_email=context.user.email
    )


@router.delete("/courses/{course_id}/enroll", status_code=status.HTTP_204_NO_CONTENT)
def unenroll_from_course(
    course_id: int,
    context: OrgContext = Depends(get_current_org_context),
    db: Session = Depends(get_db)
):
    """Unenroll the current user from a course."""
    course = get_course_or_404(db, course_id, context.org_id)
    enrollment = (
        db.query(Enrollment)
        .filter(
            Enrollment.user_id == context.user.id,
            Enrollment.course_id == course.id,
            Enrollment.org_id == context.org_id
        )
        .first()
    )
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not enrolled in this course"
        )

    db.delete(enrollment)
    db.commit()
    return None


@router.get("/me/learning", response_model=List[MyLearningCourse])
def get_my_learning(
    context: OrgContext = Depends(get_current_org_context),
    db: Session = Depends(get_db)
):
    """Get all courses the current user is enrolled in within the active organization, with progress %."""
    enrollments = (
        db.query(Enrollment, Course)
        .join(Course, Enrollment.course_id == Course.id)
        .filter(
            Enrollment.user_id == context.user.id,
            Enrollment.org_id == context.org_id
        )
        .order_by(Enrollment.enrolled_at.desc())
        .all()
    )

    result = []
    for enr, crs in enrollments:
        # Total lessons in this course
        total_lessons = db.query(Lesson).filter(Lesson.course_id == crs.id).count()

        # Completed lessons by this user in this course
        completed_lessons = (
            db.query(LessonProgress)
            .join(Lesson, LessonProgress.lesson_id == Lesson.id)
            .filter(
                Lesson.course_id == crs.id,
                LessonProgress.user_id == context.user.id
            )
            .count()
        )

        progress_pct = (
            round((completed_lessons / total_lessons) * 100, 1)
            if total_lessons > 0
            else 0.0
        )

        result.append(
            MyLearningCourse(
                course_id=crs.id,
                title=crs.title,
                description=crs.description or "",
                enrolled_at=enr.enrolled_at,
                total_lessons=total_lessons,
                completed_lessons=completed_lessons,
                progress_percentage=progress_pct
            )
        )

    return result


@router.post("/lessons/{lesson_id}/complete")
def toggle_lesson_complete(
    lesson_id: int,
    context: OrgContext = Depends(get_current_org_context),
    db: Session = Depends(get_db)
):
    """Mark a lesson as complete (or toggle it).
    
    Verifies that the parent course belongs to the active organization.
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")

    course = db.query(Course).filter(Course.id == lesson.course_id, Course.org_id == context.org_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")

    progress = (
        db.query(LessonProgress)
        .filter(
            LessonProgress.user_id == context.user.id,
            LessonProgress.lesson_id == lesson_id
        )
        .first()
    )

    if progress:
        # If already completed, uncomplete it
        db.delete(progress)
        db.commit()
        return {"lesson_id": lesson_id, "is_completed": False}
    else:
        # Mark as complete
        new_progress = LessonProgress(
            user_id=context.user.id,
            lesson_id=lesson_id
        )
        db.add(new_progress)
        db.commit()
        return {"lesson_id": lesson_id, "is_completed": True}


@router.get("/courses/{course_id}/enrollments", response_model=List[EnrollmentOut])
def get_course_enrollments(
    course_id: int,
    context: OrgContext = Depends(require_role("admin", "instructor")),
    db: Session = Depends(get_db)
):
    """View enrollment list for a course (Admin or course instructor)."""
    course = get_course_or_404(db, course_id, context.org_id)
    verify_course_write_permission(course, context)

    enrollments = (
        db.query(Enrollment, User)
        .join(User, Enrollment.user_id == User.id)
        .filter(
            Enrollment.course_id == course.id,
            Enrollment.org_id == context.org_id
        )
        .all()
    )

    return [
        EnrollmentOut(
            id=enr.id,
            user_id=enr.user_id,
            course_id=enr.course_id,
            org_id=enr.org_id,
            enrolled_at=enr.enrolled_at,
            user_name=usr.full_name,
            user_email=usr.email
        )
        for enr, usr in enrollments
    ]
