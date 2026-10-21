# Technical Requirements Document (TRD) / Tech Stack

**Product:** OrgLearn — Multi-Org Learning Platform
**Status:** Draft v1

> **Versions:** the ranges below are the minimums to target. After installing, run `pip freeze` and commit exact pins to `requirements.txt`. Check the current stable release of each library at install time.

---

## 1. Architecture Overview

```
┌──────────────┐   HTTPS/JSON    ┌───────────────────┐    SQLAlchemy    ┌────────────┐
│  Streamlit   │ ──────────────► │      FastAPI      │ ───────────────► │   SQLite   │
│  (frontend)  │ ◄────────────── │  (REST API + auth)│ ◄─────────────── │ orglearn.db│
└──────────────┘  Bearer JWT     └───────────────────┘                  └────────────┘
  st.session_state                 routers → services → models
```

- **Frontend (Streamlit)** holds no business rules. It calls the API with `requests`/`httpx` and stores the JWT and selected org in `st.session_state`.
- **Backend (FastAPI)** owns authentication, authorization and all business rules.
- **Database (SQLite)** accessed through SQLAlchemy ORM; schema created by Alembic migrations (or `create_all` for the MVP).

## 2. Tech Stack

| Layer | Choice | Target version | Purpose |
|---|---|---|---|
| Language | Python | 3.11+ | Both frontend and backend |
| API framework | FastAPI | 0.115+ | REST API, automatic OpenAPI docs |
| ASGI server | Uvicorn | 0.30+ | Runs FastAPI |
| Validation | Pydantic | 2.x | Request/response schemas |
| ORM | SQLAlchemy | 2.x | Models and queries |
| Migrations | Alembic | 1.13+ | Schema versioning (optional for MVP) |
| Database | SQLite | 3.x (bundled with Python) | Local, file-based storage |
| Auth | python-jose or PyJWT | latest stable | JWT creation/verification |
| Password hashing | passlib[bcrypt] or bcrypt | latest stable | Hash passwords |
| Frontend | Streamlit | 1.40+ | UI |
| HTTP client | httpx or requests | latest stable | Streamlit → API calls |
| Config | pydantic-settings | 2.x | Environment variables |
| Testing | pytest, pytest-cov, httpx (TestClient) | latest stable | Unit and API tests |
| API testing | Postman | — | Collection exported to `/postman` |
| Lint/format | ruff, black | latest stable | Code quality |
| CI | GitHub Actions | — | Run lint + tests on every PR |
| Hosting (API) | Azure App Service (Linux, Python) | — | Deployment target |
| Hosting (UI) | Streamlit Community Cloud or a second App Service | — | Deployment target |

## 3. Repository Structure

```
orglearn/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, router registration, CORS
│   │   ├── core/
│   │   │   ├── config.py        # settings from env
│   │   │   ├── security.py      # hashing, JWT create/decode
│   │   │   └── deps.py          # get_db, get_current_user, require_role(...)
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   └── session.py
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── routers/             # auth.py, orgs.py, members.py, courses.py, lessons.py, enrollments.py
│   │   └── services/            # business rules (permissions, last-admin check, progress)
│   ├── tests/
│   │   ├── conftest.py          # test DB, client, seed helpers
│   │   ├── test_auth.py
│   │   ├── test_org_selection.py
│   │   ├── test_permissions.py
│   │   ├── test_isolation.py
│   │   └── test_courses.py
│   └── requirements.txt
├── frontend/
│   ├── app.py                   # entry (login)
│   ├── api_client.py            # all HTTP calls in one place
│   ├── state.py                 # session_state helpers
│   └── pages/
│       ├── 1_Select_Org.py
│       ├── 2_Dashboard.py
│       ├── 3_Courses.py
│       ├── 4_My_Learning.py
│       └── 5_Members.py
├── postman/orglearn.postman_collection.json
├── docs/ (PRD.md, TRD.md, APP_FLOW.md)
├── planner.md
├── TESTING.md
├── README.md
└── .github/workflows/ci.yml
```

## 4. Data Model (SQLite)

| Table | Columns | Notes |
|---|---|---|
| `users` | id PK, email UNIQUE, full_name, password_hash, created_at | |
| `organizations` | id PK, name, created_by FK→users, created_at | |
| `memberships` | id PK, user_id FK, org_id FK, role (`admin`/`instructor`/`learner`), created_at | UNIQUE(user_id, org_id) |
| `courses` | id PK, org_id FK, title, description, status (`draft`/`published`), created_by FK→users, created_at, updated_at | index on org_id |
| `lessons` | id PK, course_id FK, title, content, position | |
| `enrollments` | id PK, user_id FK, course_id FK, org_id FK, enrolled_at | UNIQUE(user_id, course_id) |
| `lesson_progress` | id PK, user_id FK, lesson_id FK, completed_at | UNIQUE(user_id, lesson_id) |

**SQLite notes**
- Enable foreign keys on every connection: `PRAGMA foreign_keys = ON`.
- Use `check_same_thread=False` with a session-per-request pattern.
- Roles stored as strings with a CHECK constraint.

## 5. Authentication and Authorization Design

**Two-step token flow**

1. `POST /auth/login` → returns a **user token** (claims: `sub`=user_id, `type`="user") and the list of the user's organizations with roles.
2. `POST /auth/select-org` (requires user token) with `{org_id}` → verifies membership → returns an **org token** (claims: `sub`, `org_id`, `role`, `type`="org").
3. All organization endpoints require an **org token**. `org_id` and `role` come **only** from the token.
4. On each request the dependency also re-checks the membership row, so removing a member takes effect immediately (AC6).

**Token settings:** HS256, expiry 60 minutes (configurable), secret from `JWT_SECRET` env var.

**Authorization:** a reusable dependency such as `require_role("admin", "instructor")`. Ownership rules (instructor edits only own courses) live in the service layer.

**Error semantics:** 401 invalid/missing token · 403 authenticated but not allowed · 404 resource not found *or in another organization* · 409 conflict (duplicate membership, last admin) · 422 validation error.

## 6. API Specification (MVP)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | none | Create account |
| POST | `/auth/login` | none | Returns user token + organizations |
| POST | `/auth/select-org` | user token | Returns org token |
| GET | `/me` | user/org token | Current user and memberships |
| POST | `/orgs` | user token | Create org (creator becomes admin) |
| GET | `/members` | org: admin | List members |
| POST | `/members` | org: admin | Add existing user by email with role |
| PATCH | `/members/{user_id}` | org: admin | Change role (last-admin rule) |
| DELETE | `/members/{user_id}` | org: admin | Remove member (last-admin rule) |
| GET | `/courses` | org: any | List courses visible to the role |
| POST | `/courses` | org: admin, instructor | Create course |
| GET | `/courses/{id}` | org: any | Course detail with lessons |
| PATCH | `/courses/{id}` | org: admin, instructor(own) | Edit / publish |
| DELETE | `/courses/{id}` | org: admin, instructor(own) | Delete |
| POST | `/courses/{id}/lessons` | org: admin, instructor(own) | Add lesson |
| PATCH | `/lessons/{id}` | org: admin, instructor(own) | Edit lesson |
| DELETE | `/lessons/{id}` | org: admin, instructor(own) | Delete lesson |
| POST | `/courses/{id}/enroll` | org: any | Enroll |
| DELETE | `/courses/{id}/enroll` | org: any | Unenroll |
| GET | `/me/learning` | org: any | Enrolled courses with progress |
| POST | `/lessons/{id}/complete` | org: any | Mark lesson complete |
| GET | `/courses/{id}/enrollments` | org: admin, instructor(own) | Enrollment list |

OpenAPI docs are served automatically at `/docs`.

## 7. Environment Variables

| Variable | Example | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./orglearn.db` | |
| `JWT_SECRET` | (random 32+ chars) | Never commit |
| `JWT_EXPIRE_MINUTES` | `60` | |
| `API_BASE_URL` | `http://localhost:8000` | Used by Streamlit |
| `CORS_ORIGINS` | `http://localhost:8501` | |

Provide a `.env.example`; keep `.env` in `.gitignore`.

## 8. Testing Strategy

- **Unit tests:** security helpers, last-admin rule, progress calculation.
- **API tests (pytest + TestClient):** a fresh in-memory or temp SQLite per test session; fixtures create two organizations, three roles and two users.
- **Must-have cases:** every row of the PRD permission matrix; cross-org isolation for every list and detail endpoint; token tampering and expiry; removed-member access.
- **Coverage target:** 80%+ on `services/` and `routers/`.
- **Manual/exploratory:** Postman collection with environment variables for tokens; results logged in `TESTING.md`.

## 9. CI/CD

GitHub Actions workflow on push and pull request:
1. Set up Python 3.11
2. Install `requirements.txt`
3. Run `ruff` and `black --check`
4. Run `pytest --cov`
5. (Later) Deploy job to Azure App Service on merge to `main`

## 10. Deployment

- **API:** Azure App Service (Linux, Python). Startup command: `uvicorn app.main:app --host 0.0.0.0 --port 8000`. Secrets in App Service configuration, not in code.
- **UI:** Streamlit Community Cloud (simple) or a second App Service; set `API_BASE_URL` to the deployed API.
- **SQLite caveat:** App Service storage may not persist across redeploys or scale-out. For the demo, seed data on startup. State in the README that PostgreSQL is the production path.

## 11. Security Checklist

- [ ] Passwords hashed with bcrypt, never logged
- [ ] JWT secret from environment
- [ ] org_id and role never read from request bodies or query strings
- [ ] Every org query filtered by `org_id`
- [ ] Pydantic validation on all inputs
- [ ] CORS limited to the Streamlit origin
- [ ] Generic login error message (no user enumeration)
- [ ] No secrets in Git history
