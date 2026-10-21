# OrgLearn — Multi-Org Learning Platform

OrgLearn is a lightweight, multi-tenant learning management system (LMS) demonstrating strict data isolation and role-based access control (RBAC). A single user can belong to multiple organizations, select an active organization upon logging in, and have their actions restricted server-side based on their role in that organization (`admin`, `instructor`, `learner`).

---

## Architecture Overview

```
┌──────────────┐   HTTPS/JSON    ┌───────────────────┐    SQLAlchemy    ┌────────────┐
│  Streamlit   │ ──────────────► │      FastAPI      │ ───────────────► │   SQLite   │
│  (frontend)  │ ◄────────────── │  (REST API + auth)│ ◄─────────────── │ orglearn.db│
└──────────────┘  Bearer JWT     └───────────────────┘                  └────────────┘
  st.session_state                 routers → services → models
```

- **Frontend (Streamlit)**: Stateless UI. Communicates with the API using Bearer JWT tokens stored in `st.session_state`.
- **Backend (FastAPI)**: Enforces authentication, tenant isolation, and RBAC rules server-side.
- **Database (SQLite)**: File-based local storage accessed via SQLAlchemy 2.0 ORM with enforced foreign key constraints (`PRAGMA foreign_keys = ON`).

---

## User Roles & Permission Matrix

| Action | Admin | Instructor | Learner |
|---|:---:|:---:|:---:|
| View organization dashboard | ✅ | ✅ | ✅ |
| Manage members (invite, update role, remove) | ✅ | ❌ | ❌ |
| Create a course | ✅ | ✅ | ❌ |
| Edit/delete course | ✅ (any) | ✅ (own only) | ❌ |
| Manage lessons in course | ✅ | ✅ (own only) | ❌ |
| Publish/unpublish course | ✅ | ✅ (own only) | ❌ |
| View published courses | ✅ | ✅ | ✅ |
| View draft courses | ✅ | ✅ (own only) | ❌ |
| Enroll in course | ✅ | ✅ | ✅ |
| Mark lesson complete | ✅ | ✅ | ✅ |
| View course enrollments | ✅ | ✅ (own only) | ❌ |
| Access other organizations' data | ❌ | ❌ | ❌ |

---

## Project Structure

```
OrgLearn/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entrypoint
│   │   ├── core/                # Settings, security, dependencies
│   │   ├── db/                  # SQLite connection and session setup
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── routers/             # API endpoints (auth, orgs, members, courses, etc.)
│   │   └── services/            # Business logic & isolation checks
│   └── tests/                   # Pytest test suite
├── frontend/
│   ├── app.py                   # Streamlit login/register entrypoint
│   ├── api_client.py            # API client module
│   ├── state.py                 # Session state helpers
│   └── pages/                   # Multi-page Streamlit views
├── docs/                        # PRD, TRD, and APP_FLOW documentation
├── postman/                     # Postman collections
├── planner.md                   # Phased implementation roadmap
├── requirements.txt             # Project dependencies
└── README.md
```

---

## Quickstart & Local Setup

### 1. Prerequisites
- Python 3.11+ (Python 3.14 supported)
- Git

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/PalakshiVerma/OrgLearn.git
cd OrgLearn

# Create and activate virtual environment
python -m venv .venv
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy the example environment file:
```bash
cp .env.example .env
```
*(On Windows PowerShell: `Copy-Item .env.example .env`)*

### 4. Running the Application (Coming in Phases 1–4)
- **Backend API**:
  ```bash
  uvicorn backend.app.main:app --reload --port 8000
  ```
  API documentation will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

- **Frontend Streamlit UI**:
  ```bash
  streamlit run frontend/app.py
  ```
