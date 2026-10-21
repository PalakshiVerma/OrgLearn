"""Courses Page - Catalog, Course Details, Lesson Viewer, and Management."""
import streamlit as st
from frontend.api_client import api
from frontend.state import require_org, render_sidebar

st.set_page_config(
    page_title="OrgLearn — Courses",
    page_icon="📚",
    layout="wide"
)

require_org()
render_sidebar()

role = st.session_state["current_role"]
org_token = st.session_state["org_token"]
user_id = st.session_state["user"]["id"]

st.title("📚 Courses Catalog")

# Check if a course is selected for detail view
selected_course_id = st.session_state.get("selected_course_id")

if selected_course_id:
    # --- COURSE DETAIL VIEW ---
    with st.spinner("Loading course details..."):
        ok, course, code = api.get_course(org_token, selected_course_id)

    if not ok:
        st.error(f"Could not load course: {course}")
        if st.button("⬅️ Back to Courses List"):
            st.session_state["selected_course_id"] = None
            st.rerun()
        st.stop()

    if st.button("⬅️ Back to All Courses"):
        st.session_state["selected_course_id"] = None
        st.rerun()

    # Course Header
    status_color = "🟢 Published" if course["status"] == "published" else "🟡 Draft"
    st.subheader(f"{course['title']}  ({status_color})")
    if course.get("description"):
        st.markdown(f"*{course['description']}*")

    # Action Row: Enroll / Unenroll & Admin/Instructor controls
    col_act1, col_act2, col_act3 = st.columns([2, 2, 2])

    with col_act1:
        if course["is_enrolled"]:
            if st.button("❌ Unenroll from Course", key="btn_unenroll"):
                with st.spinner("Unenrolling..."):
                    ok_un, _, _ = api.unenroll(org_token, selected_course_id)
                if ok_un:
                    st.toast("Unenrolled successfully!")
                    st.rerun()
                else:
                    st.error("Failed to unenroll.")
        else:
            if st.button("✅ Enroll in Course", key="btn_enroll", type="primary"):
                with st.spinner("Enrolling..."):
                    ok_en, _, _ = api.enroll(org_token, selected_course_id)
                if ok_en:
                    st.toast("Enrolled successfully!", icon="🎉")
                    st.rerun()
                else:
                    st.error("Failed to enroll.")

    can_manage = role == "admin" or (role == "instructor" and course.get("created_by") == user_id)

    with col_act2:
        if can_manage:
            new_status = "draft" if course["status"] == "published" else "published"
            label = "Switch to Draft" if course["status"] == "published" else "🚀 Publish Course"
            if st.button(label, key="btn_toggle_status"):
                with st.spinner("Updating status..."):
                    ok_up, _, _ = api.update_course(org_token, selected_course_id, status=new_status)
                if ok_up:
                    st.toast(f"Course is now {new_status}!")
                    st.rerun()

    with col_act3:
        if can_manage:
            with st.popover("🗑️ Delete Course"):
                st.warning("Are you sure? This will delete all lessons and enrollments.")
                if st.button("Yes, Delete Course", key="btn_confirm_delete", type="primary"):
                    with st.spinner("Deleting..."):
                        ok_del, _, _ = api.delete_course(org_token, selected_course_id)
                    if ok_del:
                        st.toast("Course deleted.")
                        st.session_state["selected_course_id"] = None
                        st.rerun()

    st.markdown("---")

    # Lessons Section
    lessons = course.get("lessons", [])
    st.markdown(f"### 📑 Lessons ({len(lessons)})")

    if not lessons:
        st.info("No lessons have been added to this course yet.")
    else:
        for l in lessons:
            is_comp = l.get("is_completed", False)
            icon = "✅" if is_comp else "📖"
            with st.expander(f"{icon} Lesson {l['position']}: {l['title']}"):
                if l.get("content"):
                    st.markdown(l["content"])
                else:
                    st.caption("No content available for this lesson.")

                col_comp, col_mgmt = st.columns([2, 1])
                with col_comp:
                    btn_text = "Mark as Incomplete" if is_comp else "Mark Complete ✅"
                    if st.button(btn_text, key=f"comp_lesson_{l['id']}"):
                        with st.spinner("Updating lesson progress..."):
                            api.toggle_lesson_complete(org_token, l["id"])
                        st.rerun()

                with col_mgmt:
                    if can_manage:
                        with st.popover("⚙️ Edit / Delete Lesson"):
                            new_l_title = st.text_input("Title", value=l["title"], key=f"edit_ltitle_{l['id']}")
                            new_l_content = st.text_area("Content", value=l["content"] or "", key=f"edit_lcont_{l['id']}")
                            new_l_pos = st.number_input("Position", value=l["position"], min_value=1, step=1, key=f"edit_lpos_{l['id']}")

                            if st.button("Save Lesson Changes", key=f"save_l_{l['id']}"):
                                api.update_lesson(org_token, l["id"], title=new_l_title, content=new_l_content, position=new_l_pos)
                                st.rerun()

                            if st.button("Delete Lesson", key=f"del_l_{l['id']}", type="primary"):
                                api.delete_lesson(org_token, l["id"])
                                st.rerun()

    # Add Lesson Form (For Admin/Instructor)
    if can_manage:
        st.markdown("---")
        with st.expander("➕ Add a New Lesson to this Course"):
            with st.form(f"add_lesson_form_{selected_course_id}", clear_on_submit=True):
                l_title = st.text_input("Lesson Title", placeholder="e.g. Chapter 1: Getting Started")
                l_content = st.text_area("Lesson Content (Markdown supported)", placeholder="Write explanation, examples, and assignments...")
                l_pos = st.number_input("Position", min_value=1, value=len(lessons) + 1, step=1)
                submit_l = st.form_submit_button("Add Lesson", type="primary")

            if submit_l:
                if not l_title.strip():
                    st.error("Please enter a lesson title.")
                else:
                    with st.spinner("Adding lesson..."):
                        ok_add, res_add, _ = api.add_lesson(org_token, selected_course_id, l_title.strip(), l_content.strip(), int(l_pos))
                    if ok_add:
                        st.toast("Lesson added successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed to add lesson: {res_add}")

    # View Enrollments List (For Admin/Instructor)
    if can_manage:
        st.markdown("---")
        with st.expander("👥 View Enrolled Learners"):
            ok_enrs, enr_list, _ = api.get_course_enrollments(org_token, selected_course_id)
            if ok_enrs and enr_list:
                st.dataframe(
                    [{"User": e.get("user_name"), "Email": e.get("user_email"), "Enrolled Date": e.get("enrolled_at")} for e in enr_list],
                    use_container_width=True
                )
            else:
                st.caption("No learners have enrolled in this course yet.")

    st.stop()

# --- COURSE CATALOG VIEW ---
col_head, col_btn = st.columns([3, 1])
with col_head:
    st.markdown("Browse courses offered in your active organization.")

can_create = role in ["admin", "instructor"]

with col_btn:
    if can_create:
        with st.popover("➕ Create Course"):
            with st.form("create_course_form", clear_on_submit=True):
                c_title = st.text_input("Course Title", placeholder="e.g. Advanced System Design")
                c_desc = st.text_area("Description", placeholder="Summary of course goals...")
                c_status = st.selectbox("Initial Status", options=["draft", "published"])
                submit_create = st.form_submit_button("Create Course", type="primary", use_container_width=True)

            if submit_create:
                if not c_title.strip():
                    st.error("Course title is required.")
                else:
                    with st.spinner("Creating course..."):
                        ok_c, res_c, _ = api.create_course(org_token, c_title.strip(), c_desc.strip(), c_status)
                    if ok_c:
                        st.toast("Course created successfully!", icon="🎉")
                        st.rerun()
                    else:
                        st.error(f"Failed to create course: {res_c}")

# Fetch Courses
with st.spinner("Loading courses..."):
    ok, courses, code = api.list_courses(org_token)

if not ok:
    st.error(f"Error fetching courses: {courses}")
    st.stop()

if not courses:
    st.info("No courses found in this organization.")
    if can_create:
        st.markdown("Use the **➕ Create Course** button above to get started.")
else:
    for c in courses:
        status_badge = "🟢 Published" if c["status"] == "published" else "🟡 Draft"
        enrolled_badge = " · [Enrolled]" if c.get("is_enrolled") else ""

        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"### {c['title']}")
                if c.get("description"):
                    st.markdown(c["description"])
            with col2:
                st.markdown(f"**Status:** `{status_badge}`{enrolled_badge}")
                st.caption(f"📑 {c.get('lessons_count', 0)} Lessons")
            with col3:
                if st.button("📖 Open Course", key=f"btn_open_{c['id']}", use_container_width=True, type="primary"):
                    st.session_state["selected_course_id"] = c["id"]
                    st.rerun()
