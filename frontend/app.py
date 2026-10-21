"""OrgLearn - Multi-Org Learning Platform - Login & Register Entry Point."""
import streamlit as st
from frontend.api_client import api
from frontend.state import init_session_state, is_logged_in, set_user_session, render_sidebar

st.set_page_config(
    page_title="OrgLearn — Login",
    page_icon="🎓",
    layout="centered"
)

init_session_state()

# If already logged in, show options or redirect
if is_logged_in():
    render_sidebar()
    st.title("🎓 OrgLearn")
    st.success(f"You are already signed in as **{st.session_state['user'].get('full_name')}** ({st.session_state['user'].get('email')}).")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👉 Continue to Organization Selection", use_container_width=True, type="primary"):
            st.switch_page("pages/1_Select_Org.py")
    with col2:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            init_session_state()
            st.rerun()
    st.stop()

# Header & Branding
st.title("🎓 OrgLearn")
st.subheader("Multi-Organization Learning Platform")
st.caption("Demonstrating strict multi-tenant isolation and role-based access control (RBAC).")

tab_login, tab_register = st.tabs(["🔑 Sign In", "📝 Create Account"])

# --- TAB 1: LOGIN ---
with tab_login:
    st.markdown("### Welcome Back")
    with st.form("login_form", clear_on_submit=False):
        login_email = st.text_input("Email Address", placeholder="name@organization.com")
        login_password = st.text_input("Password", type="password", placeholder="••••••••")
        submitted_login = st.form_submit_button("Sign In", use_container_width=True, type="primary")

    if submitted_login:
        if not login_email or not login_password:
            st.error("Please fill in both email and password.")
        else:
            with st.spinner("Authenticating..."):
                ok, resp, code = api.login(login_email.strip(), login_password)

            if ok:
                st.toast("Login successful!", icon="✅")
                user_token = resp["access_token"]
                user_data = resp["user"]
                organizations = resp.get("organizations", [])

                set_user_session(user_token, user_data, organizations)
                st.switch_page("pages/1_Select_Org.py")
            else:
                st.error(f"Authentication failed: {resp}")

# --- TAB 2: REGISTER ---
with tab_register:
    st.markdown("### Register a New Account")
    with st.form("register_form", clear_on_submit=False):
        reg_name = st.text_input("Full Name", placeholder="e.g. Dr. Jane Doe")
        reg_email = st.text_input("Email Address", placeholder="name@organization.com")
        reg_password = st.text_input("Password", type="password", placeholder="At least 6 characters")
        submitted_reg = st.form_submit_button("Create Account", use_container_width=True, type="primary")

    if submitted_reg:
        if not reg_name or not reg_email or not reg_password:
            st.error("Please provide all required fields.")
        elif len(reg_password) < 6:
            st.error("Password must be at least 6 characters.")
        else:
            with st.spinner("Creating account..."):
                ok, resp, code = api.register(reg_email.strip(), reg_name.strip(), reg_password)

            if ok:
                st.success("Account created successfully! You can now switch to the 'Sign In' tab to log in.")
            else:
                st.error(f"Registration failed: {resp}")

st.markdown("---")
with st.expander("ℹ️ About the Multi-Tenant Architecture"):
    st.markdown("""
    - **One User, Many Orgs**: Users can belong to multiple organizations simultaneously.
    - **Dynamic Roles**: A user may be an `admin` in one organization, an `instructor` in another, and a `learner` in a third.
    - **Strict Isolation**: When entering an organization, a scoped token is created and all course, lesson, and membership actions are strictly isolated to that tenant.
    """)
