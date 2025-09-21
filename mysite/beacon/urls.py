from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name='home'),
    path("i_login/", views.instructor_login, name="instructor_login"),
    path("login/", views.student_login, name="login"), 
    path("sign_up/", views.student_signup, name="sign_up"), 
    path("instructor/", views.instructor_dashboard, name="instructor_dashboard"), 
    path('course/add/', views.create_course, name='create_course'),
    path("course/<int:pk>/edit/", views.edit_course, name="edit_course"),
    path("course/<int:pk>/delete/", views.delete_course, name="delete_course"),
    path("student/", views.student_dashboard, name="student_dashboard"), 
    path("student/course/<int:pk>/",views.student_course_details,name="student_course_details"),
    path("student/lesson/<int:pk>/", views.student_lesson_details, name="student_lesson_details"),
    path("enrollment/", views.enrolment_page, name="enrolment_page"),
    path("enroll/<int:course_id>/", views.enrol_course, name="enrol_course"),
    path('course/<int:pk>/', views.course_detail, name='course_detail'),
    path('lesson/<int:pk>/', views.lesson_detail_edit, name='lesson_detail_edit'),
    path('course/<int:course_pk>/lesson/create/', views.create_lesson, name='create_lesson'),
    path('lesson/<int:pk>/delete/', views.delete_lesson, name='delete_lesson'),
    # student classroom
    path("classrooms/", views.student_classroom, name="student_classroom"),
    path('classroom/<int:pk>/', views.student_classroom_details, name='student_classroom_details'),
    #instructor classroom
    path("instructor/classroom/", views.instructor_classroom, name="instructor_classroom"),
    path("instructor/classroom/course/<int:pk>/add", views.create_classroom, name="create_classroom"),
    path("instructor/classroom/<int:pk>/edit", views.edit_classroom, name="edit_classroom"),
    path("student/lesson/<int:lesson_id>/enrol/", views.enrol_lesson, name="enrol_lesson"),
    ]