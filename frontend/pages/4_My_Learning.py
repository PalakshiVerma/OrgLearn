"""My Learning Page - Track enrolled courses and lesson completion progress."""
import streamlit as st
from frontend.api_client import api
from frontend.state import require_org, render_sidebar

st.set_page_config(
    page_title="OrgLearn — My Learning",
    page_icon="🎓",
    layout="wide"
)

require_org()
render_sidebar()

org_token = st.session_state["org_token"]
org_name = st.session_state["current_org_name"]

st.title(f"🎓 My Learning — {org_name}")
st.markdown("All courses you are currently enrolled in within this organization.")

with st.spinner("Fetching your learning progress..."):
    ok, learning, code = api.get_my_learning(org_token)

if not ok:
    st.error(f"Failed to load learning progress: {learning}")
    st.stop()

if not learning:
    st.info("You haven't enrolled in any courses in this organization yet.")
    if st.button("🔍 Browse Course Catalog", type="primary"):
        st.session_state["selected_course_id"] = None
        st.switch_page("pages/3_Courses.py")
else:
    for item in learning:
        with st.container(border=True):
            c_info, c_meter, c_action = st.columns([3, 2, 1])

            with c_info:
                st.markdown(f"### {item['title']}")
                if item.get("description"):
                    st.caption(item["description"])
                st.caption(f"Enrolled on: {item['enrolled_at'][:10]}")

            with c_meter:
                st.markdown("**Progress:**")
                progress_val = float(item["progress_percentage"]) / 100.0
                st.progress(progress_val)
                st.markdown(f"**{item['completed_lessons']}** of **{item['total_lessons']}** lessons completed ({item['progress_percentage']}%)")

            with c_action:
                if st.button("Continue Learning ➡️", key=f"continue_{item['course_id']}", use_container_width=True, type="primary"):
                    st.session_state["selected_course_id"] = item["course_id"]
                    st.switch_page("pages/3_Courses.py")
