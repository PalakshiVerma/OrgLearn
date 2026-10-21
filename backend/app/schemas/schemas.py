"""Pydantic schemas for Auth, Users, Organizations, Courses, Lessons, and Memberships."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# --- Auth Schemas ---
class UserRegister(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class OrgMembershipBrief(BaseModel):
    org_id: int
    org_name: str
    role: str

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"
    organizations: List[OrgMembershipBrief]


class SelectOrgRequest(BaseModel):
    org_id: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    org_id: int
    role: str


# --- User Schemas ---
class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserMeResponse(BaseModel):
    user: UserOut
    organizations: List[OrgMembershipBrief]
    active_org: Optional[OrgMembershipBrief] = None


# --- Org Schemas ---
class OrgCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class OrgOut(BaseModel):
    id: int
    name: str
    created_by: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Member Schemas ---
class MemberAdd(BaseModel):
    email: EmailStr
    role: str = Field(..., pattern="^(admin|instructor|learner)$")


class MemberUpdateRole(BaseModel):
    role: str = Field(..., pattern="^(admin|instructor|learner)$")


class MemberOut(BaseModel):
    user_id: int
    email: str
    full_name: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Lesson Schemas ---
class LessonCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: Optional[str] = ""
    position: Optional[int] = 1


class LessonUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    position: Optional[int] = None


class LessonOut(BaseModel):
    id: int
    course_id: int
    title: str
    content: Optional[str] = ""
    position: int
    is_completed: Optional[bool] = False

    model_config = {"from_attributes": True}


# --- Course Schemas ---
class CourseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = ""
    status: Optional[str] = Field("draft", pattern="^(draft|published)$")


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(draft|published)$")


class CourseOut(BaseModel):
    id: int
    org_id: int
    title: str
    description: Optional[str] = ""
    status: str
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    lessons_count: Optional[int] = 0
    is_enrolled: Optional[bool] = False

    model_config = {"from_attributes": True}


class CourseDetail(CourseOut):
    lessons: List[LessonOut] = []


# --- Learning & Enrollment Schemas ---
class EnrollmentOut(BaseModel):
    id: int
    user_id: int
    course_id: int
    org_id: int
    enrolled_at: datetime
    user_name: Optional[str] = None
    user_email: Optional[str] = None

    model_config = {"from_attributes": True}


class MyLearningCourse(BaseModel):
    course_id: int
    title: str
    description: Optional[str] = ""
    enrolled_at: datetime
    total_lessons: int
    completed_lessons: int
    progress_percentage: float


LoginResponse.model_rebuild()
