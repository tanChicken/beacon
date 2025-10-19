from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name='home'),
    # login and signup
    path("i_login/", views.instructor_login, name="instructor_login"),
    path("login/", views.student_login, name="login"), 
    path("sign_up/", views.student_signup, name="sign_up"), 
    # dashboard
    path("instructor/", views.instructor_dashboard, name="instructor_dashboard"), 
    path("student/", views.student_dashboard, name="student_dashboard"), 
    # instructor course
    path('course/<int:pk>/', views.course_detail, name='course_detail'),
    path('course/add/', views.create_course, name='create_course'),
    path("course/<int:pk>/edit/", views.edit_course, name="edit_course"),
    path("course/<int:pk>/delete/", views.delete_course, name="delete_course"),
    # instructor lesson
    path('lesson/<int:pk>/', views.lesson_detail_edit, name='lesson_detail_edit'),
    path('course/<int:course_pk>/lesson/create/', views.create_lesson, name='create_lesson'),
    path('lesson/<int:pk>/delete/', views.delete_lesson, name='delete_lesson'),
    path('lesson/<int:pk>/archive/', views.archive_lesson, name="archive_lesson"),
    # instructor classroom
    path("instructor/classroom/", views.instructor_classroom, name="instructor_classroom"),
    path("instructor/classroom/add/", views.create_classroom, name="create_classroom"),
    path("instructor/classroom/course/<int:pk>/add", views.create_classroom, name="create_classroom"),
    path("instructor/classroom/<int:pk>/edit", views.edit_classroom, name="edit_classroom"),
    path("instructor/classroom/<int:pk>/delete/", views.delete_classroom, name="delete_classroom"),
    # instructor view student profile
    path("instructor/students/", views.instructor_student_list, name="instructor_student_list"),
    path("instructor/students/<int:student_id>/", views.instructor_student_detail, name="instructor_student_detail"),
    # instructor report
    path("instructor/report/courses/", views.instructor_report, name="instructor_report"),
    path("report/course/<int:course_id>/students/", views.instructor_course_students, name="instructor_course_students"),
    path('course/<int:course_id>/chart/', views.course_bar_chart, name='course_bar_chart'),
    path("instructor/report/course/<int:course_id>/student/<int:student_id>/progress/",views.instructor_report_course_student_progress, name="instructor_report_course_student_progress"),
    path("instructor/students/<int:student_id>/overall-progress/",views.instructor_student_overall_progress, name="instructor_student_overall_progress"),
    # student course enrolment
    path("enrollment/", views.enrolment_page, name="enrolment_page"),
    path("enroll/<int:course_id>/", views.enrol_course, name="enrol_course"),
    path("student/course/<int:pk>/unenrol/", views.unenrol_course, name="unenrol_course"),
    # student course
    path("student/course/<int:pk>/",views.student_course_details,name="student_course_details"),
    # student lesson
    path("student/lesson/<int:pk>/", views.student_lesson_details, name="student_lesson_details"),
    path("student/lesson/<int:lesson_id>/enrol/", views.enrol_lesson, name="enrol_lesson"),
    path("lessons/<int:pk>/unenrol/", views.unenrol_lesson, name="unenrol_lesson"),
    path("toggle-checklist/<int:item_id>/", views.toggle_checklist_item, name="toggle_checklist"),
    # student classroom
    path("classrooms/", views.student_classroom, name="student_classroom"),
    path('classroom/<int:pk>/', views.student_classroom_details, name='student_classroom_details'),
    # student profile
    path("student/profile/", views.student_profile, name="student_profile"),
    path("student/change-password/", views.student_change_password, name="student_change_password"),
    path("toggle-status/", views.student_toggle_status, name="student_toggle_status"),
    # student report
    path("student/report/course", views.student_report_course, name="student_report_course"),
    path("student/report/course/<int:pk>/", views.student_report_course_details, name="student_report_course_details"),

    path("toggle-dark-mode/", views.toggle_dark_mode, name="toggle_dark_mode"),
    path("toggle-font-size/", views.toggle_font_size, name="toggle_font_size"),

    path("graduate/", views.graduate, name="graduate"),
    ]