"""Lessons management router."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.models import Course, Lesson
from backend.app.core.deps import require_role, OrgContext
from backend.app.schemas.schemas import LessonCreate, LessonUpdate, LessonOut
from backend.app.services.courses import get_course_or_404, verify_course_write_permission

router = APIRouter(tags=["lessons"])


def get_lesson_and_course_or_404(db: Session, lesson_id: int, org_id: int) -> tuple[Lesson, Course]:
    """Retrieve a lesson by ID, verifying that its parent course belongs to the active organization."""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )

    course = db.query(Course).filter(Course.id == lesson.course_id, Course.org_id == org_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    return lesson, course


@router.post("/courses/{course_id}/lessons", response_model=LessonOut, status_code=status.HTTP_201_CREATED)
def add_lesson(
    course_id: int,
    lesson_in: LessonCreate,
    context: OrgContext = Depends(require_role("admin", "instructor")),
    db: Session = Depends(get_db)
):
    """Add a lesson to a course (Admin or course instructor)."""
    course = get_course_or_404(db, course_id, context.org_id)
    verify_course_write_permission(course, context)

    lesson = Lesson(
        course_id=course.id,
        title=lesson_in.title,
        content=lesson_in.content or "",
        position=lesson_in.position or 1
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)

    return LessonOut(
        id=lesson.id,
        course_id=lesson.course_id,
        title=lesson.title,
        content=lesson.content,
        position=lesson.position,
        is_completed=False
    )


@router.patch("/lessons/{lesson_id}", response_model=LessonOut)
def update_lesson(
    lesson_id: int,
    lesson_in: LessonUpdate,
    context: OrgContext = Depends(require_role("admin", "instructor")),
    db: Session = Depends(get_db)
):
    """Edit lesson title, content, or position (Admin or course instructor)."""
    lesson, course = get_lesson_and_course_or_404(db, lesson_id, context.org_id)
    verify_course_write_permission(course, context)

    if lesson_in.title is not None:
        lesson.title = lesson_in.title
    if lesson_in.content is not None:
        lesson.content = lesson_in.content
    if lesson_in.position is not None:
        lesson.position = lesson_in.position

    db.commit()
    db.refresh(lesson)

    return LessonOut(
        id=lesson.id,
        course_id=lesson.course_id,
        title=lesson.title,
        content=lesson.content,
        position=lesson.position,
        is_completed=False
    )


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesson(
    lesson_id: int,
    context: OrgContext = Depends(require_role("admin", "instructor")),
    db: Session = Depends(get_db)
):
    """Delete a lesson (Admin or course instructor)."""
    lesson, course = get_lesson_and_course_or_404(db, lesson_id, context.org_id)
    verify_course_write_permission(course, context)

    db.delete(lesson)
    db.commit()
    return None
