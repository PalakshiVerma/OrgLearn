"""Centralized HTTP API client for OrgLearn Streamlit UI."""
import os
from typing import Optional, Dict, Any, Tuple
import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


class APIClient:
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url.rstrip("/")

    def _headers(self, token: Optional[str] = None) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        token: Optional[str] = None,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Any, int]:
        """Perform an HTTP request and return (success, data_or_error_msg, status_code)."""
        url = f"{self.base_url}{path}"
        headers = self._headers(token)
        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=json,
                params=params,
                timeout=10,
            )
            status_code = resp.status_code

            if status_code == 204:
                return True, None, 204

            try:
                data = resp.json()
            except Exception:
                data = resp.text

            if 200 <= status_code < 300:
                return True, data, status_code

            # Extract error message
            if isinstance(data, dict):
                error_detail = data.get("detail", str(data))
                if isinstance(error_detail, list):
                    # Pydantic validation error
                    error_detail = "; ".join([f"{e.get('loc', [''])[ -1]}: {e.get('msg', '')}" for e in error_detail])
                return False, error_detail, status_code

            return False, str(data), status_code
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to the OrgLearn API backend. Please ensure it is running.", 503
        except requests.exceptions.Timeout:
            return False, "Request timed out. Please try again.", 504
        except Exception as e:
            return False, f"Unexpected error: {str(e)}", 500

    # --- Auth Endpoints ---
    def register(self, email: str, full_name: str, password: str):
        return self._request("POST", "/auth/register", json={"email": email, "full_name": full_name, "password": password})

    def login(self, email: str, password: str):
        return self._request("POST", "/auth/login", json={"email": email, "password": password})

    def select_org(self, user_token: str, org_id: int):
        return self._request("POST", "/auth/select-org", token=user_token, json={"org_id": org_id})

    # --- User & Orgs ---
    def get_me(self, token: str):
        return self._request("GET", "/me", token=token)

    def create_org(self, user_token: str, name: str):
        return self._request("POST", "/orgs", token=user_token, json={"name": name})

    def get_my_orgs(self, user_token: str):
        return self._request("GET", "/orgs", token=user_token)

    # --- Members (Admin only) ---
    def list_members(self, org_token: str):
        return self._request("GET", "/members", token=org_token)

    def add_member(self, org_token: str, email: str, role: str):
        return self._request("POST", "/members", token=org_token, json={"email": email, "role": role})

    def update_member_role(self, org_token: str, user_id: int, role: str):
        return self._request("PATCH", f"/members/{user_id}", token=org_token, json={"role": role})

    def remove_member(self, org_token: str, user_id: int):
        return self._request("DELETE", f"/members/{user_id}", token=org_token)

    # --- Courses ---
    def list_courses(self, org_token: str):
        return self._request("GET", "/courses", token=org_token)

    def create_course(self, org_token: str, title: str, description: str = "", status: str = "draft"):
        return self._request("POST", "/courses", token=org_token, json={"title": title, "description": description, "status": status})

    def get_course(self, org_token: str, course_id: int):
        return self._request("GET", f"/courses/{course_id}", token=org_token)

    def update_course(self, org_token: str, course_id: int, title: Optional[str] = None, description: Optional[str] = None, status: Optional[str] = None):
        payload = {}
        if title is not None:
            payload["title"] = title
        if description is not None:
            payload["description"] = description
        if status is not None:
            payload["status"] = status
        return self._request("PATCH", f"/courses/{course_id}", token=org_token, json=payload)

    def delete_course(self, org_token: str, course_id: int):
        return self._request("DELETE", f"/courses/{course_id}", token=org_token)

    # --- Lessons ---
    def add_lesson(self, org_token: str, course_id: int, title: str, content: str = "", position: int = 1):
        return self._request("POST", f"/courses/{course_id}/lessons", token=org_token, json={"title": title, "content": content, "position": position})

    def update_lesson(self, org_token: str, lesson_id: int, title: Optional[str] = None, content: Optional[str] = None, position: Optional[int] = None):
        payload = {}
        if title is not None:
            payload["title"] = title
        if content is not None:
            payload["content"] = content
        if position is not None:
            payload["position"] = position
        return self._request("PATCH", f"/lessons/{lesson_id}", token=org_token, json=payload)

    def delete_lesson(self, org_token: str, lesson_id: int):
        return self._request("DELETE", f"/lessons/{lesson_id}", token=org_token)

    # --- Enrollments & Learning ---
    def enroll(self, org_token: str, course_id: int):
        return self._request("POST", f"/courses/{course_id}/enroll", token=org_token)

    def unenroll(self, org_token: str, course_id: int):
        return self._request("DELETE", f"/courses/{course_id}/enroll", token=org_token)

    def get_my_learning(self, org_token: str):
        return self._request("GET", "/me/learning", token=org_token)

    def toggle_lesson_complete(self, org_token: str, lesson_id: int):
        return self._request("POST", f"/lessons/{lesson_id}/complete", token=org_token)

    def get_course_enrollments(self, org_token: str, course_id: int):
        return self._request("GET", f"/courses/{course_id}/enrollments", token=org_token)


api = APIClient()
