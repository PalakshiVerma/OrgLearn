"""Integration tests for Phase 2: Auth, Org Selection, and Member Management."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app

from sqlalchemy.pool import StaticPool

# Create in-memory SQLite database with StaticPool for test suite
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


def test_auth_registration_and_login(client):
    # 1. Register a new user
    reg_payload = {
        "email": "user1@example.com",
        "full_name": "User One",
        "password": "Password123!"
    }
    res_reg = client.post("/auth/register", json=reg_payload)
    assert res_reg.status_code == 201
    reg_data = res_reg.json()
    assert reg_data["email"] == "user1@example.com"
    assert "password_hash" not in reg_data

    # Duplicate registration should return 409
    res_dup = client.post("/auth/register", json=reg_payload)
    assert res_dup.status_code == 409

    # 2. Login
    login_payload = {
        "email": "user1@example.com",
        "password": "Password123!"
    }
    res_login = client.post("/auth/login", json=login_payload)
    assert res_login.status_code == 200
    login_data = res_login.json()
    assert "access_token" in login_data
    assert login_data["organizations"] == []


def test_org_creation_and_selection_flow(client):
    # Register and login user 1
    client.post("/auth/register", json={"email": "alice@org.com", "full_name": "Alice Admin", "password": "Password123!"})
    login_res = client.post("/auth/login", json={"email": "alice@org.com", "password": "Password123!"})
    user_token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {user_token}"}

    # Create Organization A
    res_org = client.post("/orgs", json={"name": "Engineering Academy"}, headers=headers)
    assert res_org.status_code == 201
    org_a = res_org.json()
    org_a_id = org_a["id"]

    # Verify user /me has the new org with admin role
    res_me = client.get("/me", headers=headers)
    assert res_me.status_code == 200
    me_data = res_me.json()
    assert len(me_data["organizations"]) == 1
    assert me_data["organizations"][0]["role"] == "admin"

    # Select Organization A
    res_select = client.post("/auth/select-org", json={"org_id": org_a_id}, headers=headers)
    assert res_select.status_code == 200
    select_data = res_select.json()
    assert select_data["org_id"] == org_a_id
    assert select_data["role"] == "admin"
    org_token = select_data["access_token"]
    org_headers = {"Authorization": f"Bearer {org_token}"}

    # /me using org token shows active_org
    res_me_org = client.get("/me", headers=org_headers)
    assert res_me_org.status_code == 200
    assert res_me_org.json()["active_org"]["org_id"] == org_a_id


def test_member_management_and_last_admin_protection(client):
    # Setup Admin Alice
    client.post("/auth/register", json={"email": "alice@org.com", "full_name": "Alice Admin", "password": "Password123!"})
    login_alice = client.post("/auth/login", json={"email": "alice@org.com", "password": "Password123!"}).json()
    alice_user_token = login_alice["access_token"]
    alice_user_headers = {"Authorization": f"Bearer {alice_user_token}"}

    # Alice creates Org
    org = client.post("/orgs", json={"name": "Acme Corp"}, headers=alice_user_headers).json()
    org_id = org["id"]

    # Alice selects Org
    alice_org_token = client.post("/auth/select-org", json={"org_id": org_id}, headers=alice_user_headers).json()["access_token"]
    alice_org_headers = {"Authorization": f"Bearer {alice_org_token}"}

    # Register Bob and Charlie
    client.post("/auth/register", json={"email": "bob@org.com", "full_name": "Bob Instructor", "password": "Password123!"})
    client.post("/auth/register", json={"email": "charlie@org.com", "full_name": "Charlie Learner", "password": "Password123!"})

    # Alice adds Bob as instructor and Charlie as learner
    res_add_bob = client.post("/members", json={"email": "bob@org.com", "role": "instructor"}, headers=alice_org_headers)
    assert res_add_bob.status_code == 201
    bob_data = res_add_bob.json()
    bob_user_id = bob_data["user_id"]

    res_add_charlie = client.post("/members", json={"email": "charlie@org.com", "role": "learner"}, headers=alice_org_headers)
    assert res_add_charlie.status_code == 201

    # List members
    res_members = client.get("/members", headers=alice_org_headers)
    assert res_members.status_code == 200
    assert len(res_members.json()) == 3

    # Try non-admin access: Bob selects org and tries to list members
    login_bob = client.post("/auth/login", json={"email": "bob@org.com", "password": "Password123!"}).json()
    bob_org_token = client.post("/auth/select-org", json={"org_id": org_id}, headers={"Authorization": f"Bearer {login_bob['access_token']}"}).json()["access_token"]
    bob_org_headers = {"Authorization": f"Bearer {bob_org_token}"}

    res_bob_forbidden = client.get("/members", headers=bob_org_headers)
    assert res_bob_forbidden.status_code == 403

    # Alice cannot demote or remove herself because she is the last admin
    alice_id = login_alice["user"]["id"]
    res_demote_alice = client.patch(f"/members/{alice_id}", json={"role": "learner"}, headers=alice_org_headers)
    assert res_demote_alice.status_code == 409
    assert "last remaining admin" in res_demote_alice.json()["detail"]

    res_delete_alice = client.delete(f"/members/{alice_id}", headers=alice_org_headers)
    assert res_delete_alice.status_code == 409

    # Promote Bob to admin
    res_promote_bob = client.patch(f"/members/{bob_user_id}", json={"role": "admin"}, headers=alice_org_headers)
    assert res_promote_bob.status_code == 200
    assert res_promote_bob.json()["role"] == "admin"

    # Now Alice can be demoted since Bob is also an admin
    res_demote_alice_ok = client.patch(f"/members/{alice_id}", json={"role": "instructor"}, headers=alice_org_headers)
    assert res_demote_alice_ok.status_code == 200
