# OrgLearn — Project Planner

> **Product:** OrgLearn — Multi-Org Learning Platform  
> **Stack:** Python, FastAPI, SQLite (SQLAlchemy 2.x), Streamlit, PyJWT / python-jose, Pydantic 2.x  
> **Architecture:** Decoupled Backend (FastAPI REST API with RBAC & multi-tenant isolation) + Frontend (Streamlit UI with Bearer JWT)

---

## Phase 0 — Scope and Setup

**Goal:** Establish a clean, reproducible project structure, virtual environment, dependencies, environment configs, and repository hygiene for OrgLearn.

- [x] Create project repository structure (`backend/`, `frontend/`, `docs/`, `postman/`).
- [x] Create and activate Python virtual environment (`.venv`).
- [x] Create `.gitignore` (ignoring `.env`, `.venv`, `__pycache__`, SQLite database `*.db`, caches, OS artifacts).
- [x] Create `requirements.txt` with target libraries (FastAPI, Uvicorn, SQLAlchemy, Pydantic, Streamlit, passlib/bcrypt, PyJWT, pytest, httpx, etc.).
- [x] Create `.env.example` with required environment variables (`DATABASE_URL`, `JWT_SECRET`, `JWT_EXPIRE_MINUTES`, `API_BASE_URL`, `CORS_ORIGINS`).
- [x] Create local `.env` with safe default development values.
- [x] Create initial `README.md` with project overview, architecture diagram, local setup instructions, and Phase 0 status.
- [x] Move existing documentation (`PRD.md`, `TRD.md`, `APP_FLOW.md`) into `docs/` or cross-reference cleanly.
- [x] Verify Python environment and dependencies install cleanly.

**Exit criteria:** A new developer can clone the repository, create/activate the virtual environment, install dependencies from `requirements.txt`, and have a ready workspace without exposed secrets.

---

## Phase 1 — Backend Core & Database Foundation

**Goal:** Implement database models, connection session, configuration settings, and core security utilities.

- [ ] Set up `backend/app/core/config.py` using `pydantic-settings`.
- [ ] Set up `backend/app/db/session.py` with SQLite connection (`PRAGMA foreign_keys = ON`, `check_same_thread=False`).
- [ ] Implement SQLAlchemy 2.0 models in `backend/app/models/`:
  - `User` (`users`)
  - `Organization` (`organizations`)
  - `Membership` (`memberships` with role `admin`, `instructor`, `learner`)
  - `Course` (`courses` with status `draft`, `published`)
  - `Lesson` (`lessons`)
  - `Enrollment` (`enrollments`)
  - `LessonProgress` (`lesson_progress`)
- [ ] Implement database initialization script / helper to create tables.
- [ ] Implement password hashing and verification in `backend/app/core/security.py`.
- [ ] Implement JWT token generation and verification for user token and org token.
- [ ] Build dependency injection in `backend/app/core/deps.py`:
  - `get_db`
  - `get_current_user`
  - `get_current_org_member` / `require_role(...)`

**Exit criteria:** Models and tables initialize cleanly, passwords hash securely, and tokens encode/decode claims properly.

---

## Phase 2 — Backend Authentication & Multi-Tenant Organization APIs

**Goal:** Build and verify user registration, login, org creation, and org selection (two-step token flow).

- [ ] Implement `POST /auth/register` (unique email, hashed password).
- [ ] Implement `POST /auth/login` (returns user token and organization list).
- [ ] Implement `POST /auth/select-org` (validates membership, returns scoped org token).
- [ ] Implement `GET /me` (returns current user and active org details).
- [ ] Implement `POST /orgs` (creates new organization and assigns creator as admin).
- [ ] Implement `backend/app/routers/members.py`:
  - `GET /members` (admin only: list org members)
  - `POST /members` (admin only: add user by email with role)
  - `PATCH /members/{user_id}` (admin only: update role, enforce last-admin rule)
  - `DELETE /members/{user_id}` (admin only: remove member, enforce last-admin rule)
- [ ] Write automated pytest suite for auth, org selection, and member management.

**Exit criteria:** Users can register, log in, create/switch orgs, and admins can manage members while protecting the last admin.

---

## Phase 3 — Backend Courses, Lessons, and Learning APIs

**Goal:** Implement course authoring, lesson management, enrollment, and progress tracking with strict RBAC and tenant isolation.

- [ ] Implement `backend/app/routers/courses.py`:
  - `GET /courses` (learners see published courses; instructors/admins see draft courses per permissions)
  - `POST /courses` (admin or instructor)
  - `GET /courses/{id}`
  - `PATCH /courses/{id}` (admin or course instructor)
  - `DELETE /courses/{id}` (admin or course instructor)
- [ ] Implement `backend/app/routers/lessons.py`:
  - `POST /courses/{id}/lessons`
  - `PATCH /lessons/{id}`
  - `DELETE /lessons/{id}`
- [ ] Implement `backend/app/routers/enrollments.py`:
  - `POST /courses/{id}/enroll`
  - `DELETE /courses/{id}/enroll`
  - `GET /me/learning` (enrolled courses with progress percentage)
  - `POST /lessons/{id}/complete`
  - `GET /courses/{id}/enrollments` (admin or course instructor)
- [ ] Write automated tests proving strict cross-organization data isolation.

**Exit criteria:** Full REST API operational with automated tests proving 100% tenant isolation and RBAC rules.

---

## Phase 4 — Frontend Streamlit App & API Client

**Goal:** Build the interactive multi-page Streamlit application consuming the FastAPI backend.

- [ ] Implement `frontend/api_client.py` handling all HTTP requests with Bearer JWT tokens.
- [ ] Implement `frontend/state.py` for managing session state, token persistence, and role guards.
- [ ] Create `frontend/app.py` (Login / Register view).
- [ ] Create `frontend/pages/1_Select_Org.py` (select active organization or create a new one).
- [ ] Create `frontend/pages/2_Dashboard.py` (role-tailored dashboard with quick links and statistics).
- [ ] Create `frontend/pages/3_Courses.py` (course catalog, lesson viewer, course/lesson creation modal for instructors/admins).
- [ ] Create `frontend/pages/4_My_Learning.py` (learner enrollments, lesson progress, completion checkboxes).
- [ ] Create `frontend/pages/5_Members.py` (admin member management, role assignment).
- [ ] Add global sidebar navigation with user profile, active org badge, "Switch Organization", and "Logout".

**Exit criteria:** Users can navigate the complete lifecycle from the Streamlit UI without encountering errors.

---

## Phase 5 — End-to-End Testing, Postman Collection & Documentation

**Goal:** Comprehensive test coverage, API collection export, and developer documentation.

- [ ] Build automated integration tests with `pytest` covering all permission matrix rows.
- [ ] Export Postman collection to `postman/orglearn.postman_collection.json`.
- [ ] Create `TESTING.md` documenting test results and execution commands.
- [ ] Finalize `README.md` with complete setup and walkthrough instructions.

**Exit criteria:** Test suite passes with >=80% coverage and full documentation is ready.
