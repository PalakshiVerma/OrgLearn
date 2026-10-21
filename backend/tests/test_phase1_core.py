"""Unit and model tests for Phase 1 verification."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.base import Base
from backend.app.models.models import User, Organization, Membership, Course, Lesson, Enrollment, LessonProgress
from backend.app.core.security import hash_password, verify_password, create_user_token, create_org_token, decode_token


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_password_hashing():
    pwd = "SecretPassword123!"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_user_and_org_tokens():
    # 1. User token
    user_token = create_user_token(user_id=42)
    decoded_user = decode_token(user_token)
    assert decoded_user["sub"] == "42"
    assert decoded_user["type"] == "user"

    # 2. Org token
    org_token = create_org_token(user_id=42, org_id=10, role="admin")
    decoded_org = decode_token(org_token)
    assert decoded_org["sub"] == "42"
    assert decoded_org["org_id"] == 10
    assert decoded_org["role"] == "admin"
    assert decoded_org["type"] == "org"


def test_model_persistence(db_session):
    # Create User
    user = User(
        email="instructor@example.com",
        full_name="Alice Instructor",
        password_hash=hash_password("pw123456")
    )
    db_session.add(user)
    db_session.commit()
    assert user.id is not None

    # Create Organization
    org = Organization(name="Acme Corp", created_by=user.id)
    db_session.add(org)
    db_session.commit()
    assert org.id is not None

    # Create Membership
    membership = Membership(user_id=user.id, org_id=org.id, role="instructor")
    db_session.add(membership)
    db_session.commit()

    # Create Course
    course = Course(org_id=org.id, title="FastAPI 101", description="Intro course", status="draft", created_by=user.id)
    db_session.add(course)
    db_session.commit()

    # Create Lesson
    lesson = Lesson(course_id=course.id, title="Lesson 1: Intro", content="Welcome!", position=1)
    db_session.add(lesson)
    db_session.commit()

    # Create Learner & Enrollment
    learner = User(email="learner@example.com", full_name="Bob Learner", password_hash=hash_password("pw123456"))
    db_session.add(learner)
    db_session.commit()

    learner_membership = Membership(user_id=learner.id, org_id=org.id, role="learner")
    db_session.add(learner_membership)
    db_session.commit()

    enrollment = Enrollment(user_id=learner.id, course_id=course.id, org_id=org.id)
    db_session.add(enrollment)
    db_session.commit()

    # Mark Progress
    progress = LessonProgress(user_id=learner.id, lesson_id=lesson.id)
    db_session.add(progress)
    db_session.commit()

    # Verify relationships
    assert len(user.memberships) == 1
    assert user.memberships[0].role == "instructor"
    assert len(org.courses) == 1
    assert org.courses[0].title == "FastAPI 101"
    assert len(course.lessons) == 1
    assert len(course.enrollments) == 1
    assert len(lesson.progress_records) == 1
