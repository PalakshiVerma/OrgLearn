"""Comprehensive tests for Phase 3: Courses, Lessons, Enrollments, RBAC, and Tenant Isolation."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app

# StaticPool in-memory SQLite database
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def register_and_get_token(client, email, name, role=None, org_id=None):
    client.post("/auth/register", json={"email": email, "full_name": name, "password": "Password123!"})
    login_res = client.post("/auth/login", json={"email": email, "password": "Password123!"}).json()
    user_token = login_res["access_token"]
    if org_id:
        org_token_res = client.post(
            "/auth/select-org",
            json={"org_id": org_id},
            headers={"Authorization": f"Bearer {user_token}"}
        ).json()
        return org_token_res["access_token"]
    return user_token


def test_course_creation_and_rbac_visibility(client):
    # 1. Setup Admin Alice and Org 1
    alice_token = register_and_get_token(client, "alice@alpha.com", "Alice Admin")
    res_org = client.post("/orgs", json={"name": "Org Alpha"}, headers={"Authorization": f"Bearer {alice_token}"})
    org_id = res_org.json()["id"]

    alice_org_token = client.post("/auth/select-org", json={"org_id": org_id}, headers={"Authorization": f"Bearer {alice_token}"}).json()["access_token"]
    alice_headers = {"Authorization": f"Bearer {alice_org_token}"}

    # 2. Add Bob (Instructor) and Charlie (Learner)
    register_and_get_token(client, "bob@alpha.com", "Bob Instructor")
    register_and_get_token(client, "charlie@alpha.com", "Charlie Learner")

    client.post("/members", json={"email": "bob@alpha.com", "role": "instructor"}, headers=alice_headers)
    client.post("/members", json={"email": "charlie@alpha.com", "role": "learner"}, headers=alice_headers)

    bob_org_token = register_and_get_token(client, "bob@alpha.com", "Bob Instructor", org_id=org_id)
    charlie_org_token = register_and_get_token(client, "charlie@alpha.com", "Charlie Learner", org_id=org_id)

    bob_headers = {"Authorization": f"Bearer {bob_org_token}"}
    charlie_headers = {"Authorization": f"Bearer {charlie_org_token}"}

    # 3. Learner Charlie cannot create a course (403)
    res_learner_create = client.post("/courses", json={"title": "Hacking 101"}, headers=charlie_headers)
    assert res_learner_create.status_code == 403

    # 4. Bob (Instructor) creates a draft course
    res_bob_create = client.post("/courses", json={"title": "Python for Beginners", "description": "Basics", "status": "draft"}, headers=bob_headers)
    assert res_bob_create.status_code == 201
    course_draft_id = res_bob_create.json()["id"]

    # 5. Alice (Admin) creates a published course
    res_alice_create = client.post("/courses", json={"title": "Data Structures", "description": "Trees and Graphs", "status": "published"}, headers=alice_headers)
    assert res_alice_create.status_code == 201
    course_pub_id = res_alice_create.json()["id"]

    # 6. Check Visibility:
    # - Charlie (Learner) sees only 1 course (the published one)
    res_charlie_list = client.get("/courses", headers=charlie_headers)
    assert len(res_charlie_list.json()) == 1
    assert res_charlie_list.json()[0]["id"] == course_pub_id

    # - Bob (Instructor) sees 2 courses (the published course + his own draft)
    res_bob_list = client.get("/courses", headers=bob_headers)
    assert len(res_bob_list.json()) == 2

    # - Alice (Admin) sees all courses
    res_alice_list = client.get("/courses", headers=alice_headers)
    assert len(res_alice_list.json()) == 2


def test_course_lessons_and_learning_lifecycle(client):
    # Setup Alice (Admin) and Org
    alice_token = register_and_get_token(client, "admin@univ.com", "Admin Univ")
    org_id = client.post("/orgs", json={"name": "Open Univ"}, headers={"Authorization": f"Bearer {alice_token}"}).json()["id"]
    alice_org_token = client.post("/auth/select-org", json={"org_id": org_id}, headers={"Authorization": f"Bearer {alice_token}"}).json()["access_token"]
    alice_headers = {"Authorization": f"Bearer {alice_org_token}"}

    # Create Course
    course = client.post("/courses", json={"title": "Web Dev Bootcamp", "status": "published"}, headers=alice_headers).json()
    course_id = course["id"]

    # Add Lessons
    l1 = client.post(f"/courses/{course_id}/lessons", json={"title": "HTML & CSS", "content": "Intro to tags", "position": 1}, headers=alice_headers).json()
    l2 = client.post(f"/courses/{course_id}/lessons", json={"title": "JavaScript Basics", "content": "Variables and loops", "position": 2}, headers=alice_headers).json()

    # Register Learner Dan
    register_and_get_token(client, "dan@univ.com", "Dan Learner")
    client.post("/members", json={"email": "dan@univ.com", "role": "learner"}, headers=alice_headers)
    dan_org_token = register_and_get_token(client, "dan@univ.com", "Dan Learner", org_id=org_id)
    dan_headers = {"Authorization": f"Bearer {dan_org_token}"}

    # Dan enrolls in the course
    res_enroll = client.post(f"/courses/{course_id}/enroll", headers=dan_headers)
    assert res_enroll.status_code == 201

    # Dan checks /me/learning
    res_learning = client.get("/me/learning", headers=dan_headers)
    assert res_learning.status_code == 200
    learning_data = res_learning.json()
    assert len(learning_data) == 1
    assert learning_data[0]["total_lessons"] == 2
    assert learning_data[0]["completed_lessons"] == 0
    assert learning_data[0]["progress_percentage"] == 0.0

    # Dan marks lesson 1 complete
    res_complete = client.post(f"/lessons/{l1['id']}/complete", headers=dan_headers)
    assert res_complete.status_code == 200
    assert res_complete.json()["is_completed"] is True

    # Progress is now 50.0%
    res_learning_after = client.get("/me/learning", headers=dan_headers).json()
    assert res_learning_after[0]["completed_lessons"] == 1
    assert res_learning_after[0]["progress_percentage"] == 50.0

    # Course detail for Dan shows lesson 1 completed and lesson 2 not completed
    detail = client.get(f"/courses/{course_id}", headers=dan_headers).json()
    assert detail["is_enrolled"] is True
    assert detail["lessons"][0]["is_completed"] is True
    assert detail["lessons"][1]["is_completed"] is False


def test_cross_organization_data_isolation(client):
    """AC3 / G3: Strict multi-tenant isolation.
    
    Org 1 (Alpha) and Org 2 (Beta) have separate courses.
    A user with access to Org 1 cannot see, enroll in, modify, or complete lessons of Org 2 courses.
    """
    # 1. Setup Org 1 (Alpha) with Alice
    alice_token = register_and_get_token(client, "alice@alpha.org", "Alice Alpha")
    org1_id = client.post("/orgs", json={"name": "Org Alpha"}, headers={"Authorization": f"Bearer {alice_token}"}).json()["id"]
    alice_org1_token = client.post("/auth/select-org", json={"org_id": org1_id}, headers={"Authorization": f"Bearer {alice_token}"}).json()["access_token"]
    alice_org1_headers = {"Authorization": f"Bearer {alice_org1_token}"}

    # Org 1 Course and Lesson
    course_org1 = client.post("/courses", json={"title": "Alpha Secret Tactics", "status": "published"}, headers=alice_org1_headers).json()
    lesson_org1 = client.post(f"/courses/{course_org1['id']}/lessons", json={"title": "Lesson Alpha 1", "position": 1}, headers=alice_org1_headers).json()

    # 2. Setup Org 2 (Beta) with Bob
    bob_token = register_and_get_token(client, "bob@beta.org", "Bob Beta")
    org2_id = client.post("/orgs", json={"name": "Org Beta"}, headers={"Authorization": f"Bearer {bob_token}"}).json()["id"]
    bob_org2_token = client.post("/auth/select-org", json={"org_id": org2_id}, headers={"Authorization": f"Bearer {bob_token}"}).json()["access_token"]
    bob_org2_headers = {"Authorization": f"Bearer {bob_org2_token}"}

    # Org 2 Course and Lesson
    course_org2 = client.post("/courses", json={"title": "Beta Proprietary Tech", "status": "published"}, headers=bob_org2_headers).json()
    lesson_org2 = client.post(f"/courses/{course_org2['id']}/lessons", json={"title": "Lesson Beta 1", "position": 1}, headers=bob_org2_headers).json()

    # 3. Isolation Checks:
    # Alice (in Org 1 scope) lists courses: must ONLY see Org 1 courses
    courses_for_alice = client.get("/courses", headers=alice_org1_headers).json()
    assert len(courses_for_alice) == 1
    assert courses_for_alice[0]["title"] == "Alpha Secret Tactics"

    # Alice tries to GET course from Org 2 -> 404 (Not Found, tenant isolated)
    res_cross_course = client.get(f"/courses/{course_org2['id']}", headers=alice_org1_headers)
    assert res_cross_course.status_code == 404

    # Alice tries to enroll in course from Org 2 -> 404
    res_cross_enroll = client.post(f"/courses/{course_org2['id']}/enroll", headers=alice_org1_headers)
    assert res_cross_enroll.status_code == 404

    # Alice tries to complete lesson from Org 2 -> 404
    res_cross_lesson = client.post(f"/lessons/{lesson_org2['id']}/complete", headers=alice_org1_headers)
    assert res_cross_lesson.status_code == 404

    # Alice tries to delete course from Org 2 -> 404
    res_cross_del = client.delete(f"/courses/{course_org2['id']}", headers=alice_org1_headers)
    assert res_cross_del.status_code == 404
