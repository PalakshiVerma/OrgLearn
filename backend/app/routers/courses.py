"""Courses management router with RBAC and multi-tenant isolation."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.db.session import get_db
from backend.app.models.models import Course, Lesson, Enrollment, LessonProgress
from backend.app.core.deps import get_current_org_context, require_role, OrgContext
from backend.app.schemas.schemas import (
    CourseCreate,
    CourseUpdate,
    CourseOut,
    CourseDetail,
    LessonOut
)
from backend.app.services.courses import get_course_or_404, verify_course_write_permission

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=List[CourseOut])
def list_courses(
    context: OrgContext = Depends(get_current_org_context),
    db: Session = Depends(get_db)
):
    """List courses in the active organization.
    
    - Admin: can see all courses (draft & published).
    - Instructor: can see all published courses + their own draft courses.
    - Learner: can only see published courses.
    """
    query = db.query(Course).filter(Course.org_id == context.org_id)

    if context.role == "admin":
        courses = query.order_by(Course.created_at.desc()).all()
    elif context.role == "instructor":
        courses = (
            query.filter(
                or_(
                    Course.status == "published",
                    Course.created_by == context.user.id
                )
            )
            .order_by(Course.created_at.desc())
            .all()
        )
    else:  # learner
        courses = (
            query.filter(Course.status == "published")
            .order_by(Course.created_at.desc())
            .all()
        )

    # Get user's enrolled course IDs in this org
    enrolled_course_ids = {
        e.course_id
        for e in db.query(Enrollment.course_id)
        .filter(Enrollment.user_id == context.user.id, Enrollment.org_id == context.org_id)
        .all()
    }

    result = []
    for c in courses:
        lessons_count = db.query(Lesson).filter(Lesson.course_id == c.id).count()
        result.append(
            CourseOut(
                id=c.id,
                org_id=c.org_id,
                title=c.title,
                description=c.description,
                status=c.status,
                created_by=c.created_by,
                created_at=c.created_at,
                updated_at=c.updated_at,
                lessons_count=lessons_count,
                is_enrolled=c.id in enrolled_course_ids
            )
        )
    return result


@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(
    course_in: CourseCreate,
    context: OrgContext = Depends(require_role("admin", "instructor")),
    db: Session = Depends(get_db)
):
    """Create a new course in the active organization (Admin or Instructor)."""
    course = Course(
        org_id=context.org_id,
        title=course_in.title,
        description=course_in.description or "",
        status=course_in.status or "draft",
        created_by=context.user.id
    )
    db.add(course)
    db.commit()
    db.refresh(course)

    return CourseOut(
        id=course.id,
        org_id=course.org_id,
        title=course.title,
        description=course.description,
        status=course.status,
        created_by=course.created_by,
        created_at=course.created_at,
        updated_at=course.updated_at,
        lessons_count=0,
        is_enrolled=False
    )


@router.get("/{course_id}", response_model=CourseDetail)
def get_course_detail(
    course_id: int,
    context: OrgContext = Depends(get_current_org_context),
    db: Session = Depends(get_db)
):
    """Get course detail with lessons in the active organization.
    
    Admins can view any course; instructors can view published or their own draft courses;
    learners can only view published courses.
    """
    course = get_course_or_404(db, course_id, context.org_id)

    # Permission check for draft visibility
    if course.status == "draft":
        if context.role == "learner":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        if context.role == "instructor" and course.created_by != context.user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )

    # Fetch lessons in position order
    lessons = (
        db.query(Lesson)
        .filter(Lesson.course_id == course.id)
        .order_by(Lesson.position.asc(), Lesson.id.asc())
        .all()
    )

    # Check which lessons are completed by the current user
    completed_lesson_ids = {
        p.lesson_id
        for p in db.query(LessonProgress.lesson_id)
        .filter(
            LessonProgress.user_id == context.user.id,
            LessonProgress.lesson_id.in_([l.id for l in lessons])
        )
        .all()
    } if lessons else set()

    # Check if enrolled
    is_enrolled = (
        db.query(Enrollment)
        .filter(
            Enrollment.user_id == context.user.id,
            Enrollment.course_id == course.id,
            Enrollment.org_id == context.org_id
        )
        .first()
        is not None
    )

    lesson_outs = [
        LessonOut(
            id=l.id,
            course_id=l.course_id,
            title=l.title,
            content=l.content or "",
            position=l.position,
            is_completed=l.id in completed_lesson_ids
        )
        for l in lessons
    ]

    return CourseDetail(
        id=course.id,
        org_id=course.org_id,
        title=course.title,
        description=course.description,
        status=course.status,
        created_by=course.created_by,
        created_at=course.created_at,
        updated_at=course.updated_at,
        lessons_count=len(lessons),
        is_enrolled=is_enrolled,
        lessons=lesson_outs
    )


@router.patch("/{course_id}", response_model=CourseOut)
def update_course(
    course_id: int,
    course_in: CourseUpdate,
    context: OrgContext = Depends(require_role("admin", "instructor")),
    db: Session = Depends(get_db)
):
    """Edit/publish/unpublish course.
    
    Admin can edit any course. Instructor can only edit their own courses.
    """
    course = get_course_or_404(db, course_id, context.org_id)
    verify_course_write_permission(course, context)

    if course_in.title is not None:
        course.title = course_in.title
    if course_in.description is not None:
        course.description = course_in.description
    if course_in.status is not None:
        course.status = course_in.status

    db.commit()
    db.refresh(course)

    lessons_count = db.query(Lesson).filter(Lesson.course_id == course.id).count()
    return CourseOut(
        id=course.id,
        org_id=course.org_id,
        title=course.title,
        description=course.description,
        status=course.status,
        created_by=course.created_by,
        created_at=course.created_at,
        updated_at=course.updated_at,
        lessons_count=lessons_count,
        is_enrolled=False
    )


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: int,
    context: OrgContext = Depends(require_role("admin", "instructor")),
    db: Session = Depends(get_db)
):
    """Delete a course and cascade delete its lessons and enrollments.
    
    Admin can delete any course. Instructor can only delete their own courses.
    """
    course = get_course_or_404(db, course_id, context.org_id)
    verify_course_write_permission(course, context)

    db.delete(course)
    db.commit()
    return None
