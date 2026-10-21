"""Streamlit session state helpers and navigation guards for OrgLearn."""
import streamlit as st


def init_session_state():
    """Ensure all required keys exist in session state."""
    defaults = {
        "user_token": None,
        "user": None,             # {"id": int, "email": str, "full_name": str}
        "org_token": None,
        "current_org_id": None,
        "current_org_name": None,
        "current_role": None,     # "admin" | "instructor" | "learner"
        "organizations": [],      # list of orgs from login/get_me
        "selected_course_id": None
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def is_logged_in() -> bool:
    return bool(st.session_state.get("user_token"))


def has_selected_org() -> bool:
    return bool(st.session_state.get("org_token") and st.session_state.get("current_org_id"))


def set_user_session(user_token: str, user_dict: dict, organizations: list):
    st.session_state["user_token"] = user_token
    st.session_state["user"] = user_dict
    st.session_state["organizations"] = organizations
    # Clear org context
    clear_org_context()


def set_org_session(org_token: str, org_id: int, org_name: str, role: str):
    st.session_state["org_token"] = org_token
    st.session_state["current_org_id"] = org_id
    st.session_state["current_org_name"] = org_name
    st.session_state["current_role"] = role
    st.session_state["selected_course_id"] = None


def clear_org_context():
    st.session_state["org_token"] = None
    st.session_state["current_org_id"] = None
    st.session_state["current_org_name"] = None
    st.session_state["current_role"] = None
    st.session_state["selected_course_id"] = None


def logout():
    """Clear all user credentials and session data."""
    st.session_state.clear()
    init_session_state()
    st.switch_page("app.py")


def require_auth():
    """Guard: redirect to Login if not logged in."""
    init_session_state()
    if not is_logged_in():
        st.warning("Please log in to continue.")
        st.switch_page("app.py")


def require_org():
    """Guard: redirect to Login if not logged in, or Select Org if no org selected."""
    require_auth()
    if not has_selected_org():
        st.info("Please select an organization first.")
        st.switch_page("pages/1_Select_Org.py")


def render_sidebar():
    """Render unified navigation and organization badge in the Streamlit sidebar."""
    init_session_state()
    if not is_logged_in():
        st.sidebar.caption("Not logged in")
        return

    user = st.session_state.get("user") or {}
    st.sidebar.markdown(f"### 👤 {user.get('full_name', 'User')}")
    st.sidebar.caption(f"Email: {user.get('email', '')}")

    if has_selected_org():
        role = st.session_state.get("current_role", "").capitalize()
        role_color = {
            "Admin": "🟣",
            "Instructor": "🔵",
            "Learner": "🟢"
        }.get(role, "⚪")

        st.sidebar.divider()
        st.sidebar.markdown(f"**🏢 Active Organization:**")
        st.sidebar.markdown(f"**{st.session_state.get('current_org_name', '')}**")
        st.sidebar.markdown(f"Role: {role_color} `{role}`")

        st.sidebar.divider()
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("🔄 Switch Org", use_container_width=True):
                clear_org_context()
                st.switch_page("pages/1_Select_Org.py")
        with col2:
            if st.button("🚪 Logout", use_container_width=True):
                logout()
    else:
        st.sidebar.divider()
        if st.sidebar.button("🚪 Logout", use_container_width=True):
            logout()
