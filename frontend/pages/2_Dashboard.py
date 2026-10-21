"""Dashboard Page - Role-tailored view for Admin, Instructor, and Learner."""
import streamlit as st
from frontend.api_client import api
from frontend.state import require_org, render_sidebar

st.set_page_config(
    page_title="OrgLearn — Dashboard",
    page_icon="📊",
    layout="wide"
)

require_org()
render_sidebar()

org_name = st.session_state["current_org_name"]
role = st.session_state["current_role"]
org_token = st.session_state["org_token"]

st.title(f"📊 Dashboard — {org_name}")
st.markdown(f"Active Role: **{role.capitalize()}**")

# Fetch data for dashboard
with st.spinner("Loading organization insights..."):
    courses_ok, courses, _ = api.list_courses(org_token)
    learning_ok, learning, _ = api.get_my_learning(org_token)
    members_ok, members, _ = api.list_members(org_token) if role == "admin" else (True, [], 200)

courses = courses if courses_ok else []
learning = learning if learning_ok else []
members = members if members_ok else []

# Metrics Row
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Courses", len(courses))
with col2:
    published_count = sum(1 for c in courses if c.get("status") == "published")
    st.metric("Published Courses", published_count)
with col3:
    st.metric("Enrolled Courses", len(learning))
with col4:
    if role == "admin":
        st.metric("Total Members", len(members))
    else:
        completed_lessons_sum = sum(item.get("completed_lessons", 0) for item in learning)
        st.metric("Lessons Completed", completed_lessons_sum)

st.markdown("---")

# Role Tailored Sections
if role == "admin":
    st.subheader("🛠️ Administrator Center")
    st.markdown("As an administrator, you have full control over organization members, settings, and all course materials.")

    c_left, c_right = st.columns(2)
    with c_left:
        with st.container(border=True):
            st.markdown("#### 👥 Organization Members")
            st.markdown(f"There are currently **{len(members)}** members in this organization.")
            if st.button("Manage Members & Roles", key="dash_btn_members", type="primary", use_container_width=True):
                st.switch_page("pages/5_Members.py")

    with c_right:
        with st.container(border=True):
            st.markdown("#### 📚 Course Management")
            draft_count = sum(1 for c in courses if c.get("status") == "draft")
            st.markdown(f"**{published_count}** published courses · **{draft_count}** draft courses.")
            if st.button("Browse & Manage Courses", key="dash_btn_courses", use_container_width=True):
                st.switch_page("pages/3_Courses.py")

elif role == "instructor":
    st.subheader("🎓 Instructor Hub")
    st.markdown("Create courses, structure lesson content, and view enrollments.")

    col_inst_left, col_inst_right = st.columns([2, 1])
    with col_inst_left:
        st.markdown("#### 📖 Courses You Can Teach")
        if not courses:
            st.info("No courses created yet. Start teaching by creating your first course!")
        else:
            for c in courses[:5]:
                status_badge = "🟢 Published" if c["status"] == "published" else "🟡 Draft"
                with st.container(border=True):
                    sc1, sc2 = st.columns([3, 1])
                    with sc1:
                        st.markdown(f"**{c['title']}** ({status_badge})")
                        st.caption(f"{c.get('lessons_count', 0)} lessons")
                    with sc2:
                        if st.button("View / Edit", key=f"dash_course_{c['id']}", use_container_width=True):
                            st.session_state["selected_course_id"] = c["id"]
                            st.switch_page("pages/3_Courses.py")

    with col_inst_right:
        with st.container(border=True):
            st.markdown("#### Quick Action")
            if st.button("➕ Create New Course", key="dash_create_course", type="primary", use_container_width=True):
                st.session_state["selected_course_id"] = None
                st.switch_page("pages/3_Courses.py")

else:  # Learner
    st.subheader("🚀 Learner Progress")
    st.markdown("Keep track of your ongoing courses and continue your learning journey.")

    if not learning:
        st.info("You haven't enrolled in any courses yet.")
        if st.button("🔍 Browse Available Courses", type="primary"):
            st.switch_page("pages/3_Courses.py")
    else:
        for item in learning:
            with st.container(border=True):
                c_title, c_prog, c_btn = st.columns([3, 2, 1])
                with c_title:
                    st.markdown(f"**{item['title']}**")
                    st.caption(f"Completed {item['completed_lessons']} of {item['total_lessons']} lessons")
                with c_prog:
                    progress_val = float(item["progress_percentage"]) / 100.0
                    st.progress(progress_val)
                    st.caption(f"{item['progress_percentage']}% complete")
                with c_btn:
                    if st.button("Resume", key=f"dash_resume_{item['course_id']}", use_container_width=True, type="primary"):
                        st.session_state["selected_course_id"] = item["course_id"]
                        st.switch_page("pages/3_Courses.py")
