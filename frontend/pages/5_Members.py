"""Members Page - Organization member and role management (Admin Only)."""
import streamlit as st
from frontend.api_client import api
from frontend.state import require_org, render_sidebar

st.set_page_config(
    page_title="OrgLearn — Members",
    page_icon="👥",
    layout="wide"
)

require_org()
render_sidebar()

role = st.session_state["current_role"]
org_token = st.session_state["org_token"]
org_name = st.session_state["current_org_name"]
current_user_id = st.session_state["user"]["id"]

# Guard: Admin Only
if role != "admin":
    st.error("⛔ Access Denied: Only organization administrators can manage members.")
    if st.button("⬅️ Return to Dashboard"):
        st.switch_page("pages/2_Dashboard.py")
    st.stop()

st.title(f"👥 Manage Members — {org_name}")
st.markdown("Invite registered users to your organization, assign roles, or remove members.")

col_left, col_right = st.columns([2, 1])

with col_right:
    with st.container(border=True):
        st.subheader("➕ Add Member")
        st.caption("Add an existing user by their registered email address.")
        with st.form("add_member_form", clear_on_submit=True):
            m_email = st.text_input("User Email", placeholder="user@domain.com")
            m_role = st.selectbox("Role", options=["learner", "instructor", "admin"])
            submit_add = st.form_submit_button("Add Member", type="primary", use_container_width=True)

        if submit_add:
            if not m_email.strip():
                st.error("Please enter an email address.")
            else:
                with st.spinner("Adding member..."):
                    ok_add, res_add, code = api.add_member(org_token, m_email.strip(), m_role)
                if ok_add:
                    st.toast(f"Added {m_email.strip()} as {m_role}!", icon="🎉")
                    st.rerun()
                else:
                    st.error(f"Failed to add member: {res_add}")

with col_left:
    st.subheader("Current Organization Members")
    with st.spinner("Loading members..."):
        ok, members, code = api.list_members(org_token)

    if not ok:
        st.error(f"Error fetching members: {members}")
        st.stop()

    for m in members:
        is_self = m["user_id"] == current_user_id
        self_badge = " *(You)*" if is_self else ""
        role_badge = {
            "admin": "🟣 Admin",
            "instructor": "🔵 Instructor",
            "learner": "🟢 Learner"
        }.get(m["role"], m["role"])

        with st.container(border=True):
            c_name, c_role, c_action = st.columns([3, 2, 2])
            with c_name:
                st.markdown(f"**{m['full_name']}**{self_badge}")
                st.caption(f"Email: {m['email']}")
            with c_role:
                st.markdown(f"**Role:** `{role_badge}`")
            with c_action:
                with st.popover("⚙️ Modify"):
                    new_role = st.selectbox(
                        "Change Role",
                        options=["learner", "instructor", "admin"],
                        index=["learner", "instructor", "admin"].index(m["role"]),
                        key=f"sel_role_{m['user_id']}"
                    )
                    if st.button("Update Role", key=f"up_btn_{m['user_id']}"):
                        if new_role != m["role"]:
                            with st.spinner("Updating role..."):
                                ok_up, res_up, _ = api.update_member_role(org_token, m["user_id"], new_role)
                            if ok_up:
                                st.toast("Role updated successfully!")
                                st.rerun()
                            else:
                                st.error(f"Error: {res_up}")

                    st.markdown("---")
                    if st.button("Remove Member", key=f"del_btn_{m['user_id']}", type="primary"):
                        with st.spinner("Removing member..."):
                            ok_del, res_del, _ = api.remove_member(org_token, m["user_id"])
                        if ok_del:
                            st.toast("Member removed.")
                            st.rerun()
                        else:
                            st.error(f"Error: {res_del}")
