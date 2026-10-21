"""Select Organization Page - Allows choosing an active organization or creating a new one."""
import streamlit as st
from frontend.api_client import api
from frontend.state import require_auth, render_sidebar, set_org_session

st.set_page_config(
    page_title="OrgLearn — Select Organization",
    page_icon="🏢",
    layout="wide"
)

require_auth()
render_sidebar()

st.title("🏢 Select Your Active Organization")
st.markdown("Choose which workspace you would like to enter. Your role and permissions are specific to each organization.")

user_token = st.session_state["user_token"]

# Refresh organization memberships
with st.spinner("Fetching your organizations..."):
    ok, org_list, code = api.get_my_orgs(user_token)

if not ok:
    st.error(f"Failed to load organizations: {org_list}")
    org_list = []
else:
    st.session_state["organizations"] = org_list

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader(f"Your Memberships ({len(org_list)})")

    if not org_list:
        st.info("👋 You are not a member of any organization yet. Create your first organization using the form on the right!")
    else:
        for org in org_list:
            role = org["role"]
            role_badge = {
                "admin": "🟣 Admin",
                "instructor": "🔵 Instructor",
                "learner": "🟢 Learner"
            }.get(role.lower(), role)

            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 2])
                with c1:
                    st.markdown(f"### {org['org_name']}")
                with c2:
                    st.markdown(f"**Role:** `{role_badge}`")
                with c3:
                    if st.button("🚀 Enter Workspace", key=f"enter_org_{org['org_id']}", use_container_width=True, type="primary"):
                        with st.spinner("Acquiring organization credentials..."):
                            ok_sel, sel_resp, s_code = api.select_org(user_token, org["org_id"])
                        if ok_sel:
                            set_org_session(
                                org_token=sel_resp["access_token"],
                                org_id=org["org_id"],
                                org_name=org["org_name"],
                                role=org["role"]
                            )
                            st.toast(f"Entered {org['org_name']} as {org['role']}!", icon="🎉")
                            st.switch_page("pages/2_Dashboard.py")
                        else:
                            st.error(f"Error selecting organization: {sel_resp}")

with col_right:
    st.subheader("➕ Create New Organization")
    with st.form("create_org_form", clear_on_submit=True):
        new_org_name = st.text_input("Organization Name", placeholder="e.g. Stanford AI Lab")
        create_btn = st.form_submit_button("Create Organization", use_container_width=True)

    if create_btn:
        if not new_org_name.strip():
            st.error("Please enter a valid organization name.")
        else:
            with st.spinner("Creating organization..."):
                ok_create, create_resp, c_code = api.create_org(user_token, new_org_name.strip())
            if ok_create:
                st.success(f"Organization '{new_org_name.strip()}' created! You have been assigned as Admin.")
                st.rerun()
            else:
                st.error(f"Failed to create organization: {create_resp}")
