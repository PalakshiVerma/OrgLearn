# Product Requirements Document (PRD)

**Product:** OrgLearn — Multi-Org Learning Platform (working name)
**Owner:** Palakshi Verma
**Status:** Draft v1
**Stack (summary):** Streamlit (UI) · FastAPI (API) · SQLite (DB) · JWT auth

---

## 1. Purpose

OrgLearn is a mini learning management system (LMS) where **one user can belong to several organizations**, choose which organization to work in after login, and see different data and actions depending on their **role in that organization** (admin, instructor, learner).

It is a portfolio project that demonstrates multi-tenant data isolation, role-based access control (RBAC), REST API design and test-driven QA thinking.

## 2. Problem Statement

Learning platforms used by institutions and enterprises serve many organizations at once. The same person may be an instructor at one organization and a learner at another. The product must:

- keep every organization's data strictly separate,
- give each person only the actions their role allows in the selected organization,
- make switching organizations simple and safe.

## 3. Target Audience

| Persona | Description | Main goal |
|---|---|---|
| **Org Admin** | Manages an organization | Add members, assign roles, oversee courses |
| **Instructor** | Creates and teaches courses | Create courses and lessons, see who is enrolled |
| **Learner** | Takes courses | Browse, enroll, read lessons, track progress |
| **Reviewer (secondary)** | Recruiter or interviewer evaluating the project | Quickly see multi-org login, roles and tests working |

## 4. Goals and Non-Goals

**Goals**
- G1. A user with memberships in 2+ organizations can log in, pick an organization and see only that organization's data.
- G2. Every API endpoint enforces role-based permissions server-side.
- G3. Cross-organization data access is impossible, and this is proven by automated tests.
- G4. Anyone can run the project locally in under 10 minutes using the README.

**Non-Goals** (see section 8 for the explicit exclusion list)
- Replacing a production LMS, handling payments, or scaling beyond a demo.

## 5. User Roles and Permissions

| Action | Admin | Instructor | Learner |
|---|:-:|:-:|:-:|
| View organization dashboard | ✅ | ✅ | ✅ |
| Invite/add members, change roles, remove members | ✅ | ❌ | ❌ |
| Create a course | ✅ | ✅ | ❌ |
| Edit/delete a course | ✅ (any) | ✅ (own only) | ❌ |
| Add/edit lessons in a course | ✅ | ✅ (own courses) | ❌ |
| Publish/unpublish a course | ✅ | ✅ (own) | ❌ |
| View published courses | ✅ | ✅ | ✅ |
| View unpublished (draft) courses | ✅ | ✅ (own) | ❌ |
| Enroll in a course | ✅ | ✅ | ✅ |
| Mark a lesson complete | ✅ | ✅ | ✅ |
| View enrollment list of a course | ✅ | ✅ (own) | ❌ |
| Access any other organization's data | ❌ | ❌ | ❌ |

## 6. MVP Scope (what is included)

### 6.1 Authentication and organizations
- **F1. Register / Login** with email and password (hashed).
- **F2. Org selection:** after login, the user sees the organizations they belong to and their role in each, and picks one.
- **F3. Switch organization** without logging out.
- **F4. Create organization:** a user can create a new organization and becomes its admin.
- **F5. Logout.**

### 6.2 Member management (Admin)
- **F6. Add an existing user to the organization** by email with a chosen role.
- **F7. Change a member's role** and **remove a member**.
- **F8. Safeguard:** an organization must always keep at least one admin.

### 6.3 Courses and lessons
- **F9. Create / edit / delete course** (title, description, status: draft or published).
- **F10. Add / edit / reorder / delete text lessons** inside a course.
- **F11. Course list** filtered by the selected organization and the user's role.
- **F12. Course detail page** with lessons.

### 6.4 Learning
- **F13. Enroll / unenroll** in a published course.
- **F14. Mark lesson complete** and show course progress (%).
- **F15. "My learning" page** listing enrolled courses and progress.

### 6.5 Quality features
- **F16. Consistent error responses** (401 not logged in, 403 not allowed, 404 not found, 422 validation).
- **F17. Automated tests** for authentication, org selection and every permission rule.
- **F18. Postman collection** and **TESTING.md** with test cases and sample bug reports.

## 7. Acceptance Criteria (key ones)

| ID | Criteria |
|---|---|
| AC1 | A user in two organizations sees a different course list after switching organizations. |
| AC2 | A learner calling an admin-only endpoint receives **403**. |
| AC3 | Requesting a course that belongs to another organization returns **404** (the existence is not leaked). |
| AC4 | An instructor cannot edit a course created by another instructor (403), but an admin can. |
| AC5 | A token without a selected organization cannot access organization data (403). |
| AC6 | After a member is removed, their existing token no longer grants access to that organization's data. |
| AC7 | The last admin of an organization cannot be demoted or removed. |
| AC8 | Passwords are never stored or returned in plain text. |
| AC9 | All tests pass in CI on every pull request. |

## 8. Explicitly Out of Scope (for the MVP)

- Payments, subscriptions or billing
- Video/file upload, SCORM, or rich media lessons (text only)
- Email sending, password reset by email, email verification
- Notifications, chat, discussion forums
- Grading, certificates, quizzes (possible future work)
- Social login / SSO / OAuth
- Multi-language support, mobile app
- Advanced analytics dashboards
- Real-time features

## 9. Non-Functional Requirements

- **Security:** hashed passwords (bcrypt), JWT with expiry, org and role read from the token only (never from the request body), input validation, no secrets in the repository.
- **Data isolation:** every query on organization data is filtered by `org_id`.
- **Performance:** pages respond in under 1 second for demo-sized data.
- **Reliability:** database constraints (foreign keys, unique memberships) enforce integrity.
- **Maintainability:** clear folder structure, type hints, README, commit messages in a consistent style.
- **Testability:** business rules live in service functions that can be tested without the UI.

## 10. Success Metrics

- 100% of permission-matrix rules covered by at least one automated test.
- CI green on the main branch.
- A new user can complete "register → create org → create course → switch org" in under 3 minutes.
- Live demo link and demo credentials listed in the README.

## 11. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Cross-organization data leak through a missed `org_id` filter | Central dependency that provides `org_id`; tests for every list/detail endpoint |
| Scope creep | Stick to section 6; log new ideas under "Future work" |
| SQLite limitations in hosting (file storage may be ephemeral) | Document this; seed the demo data on startup; note PostgreSQL as the production path |
| Streamlit reruns and session handling | Keep token and selected org in `st.session_state`; centralize API calls in one client module |

## 12. Future Work (not committed)

- Quiz module with AI-generated questions and an evaluation set
- Invitations by email, password reset
- Audit log of admin actions
- Migration to PostgreSQL and Azure deployment with managed secrets
