from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name='home'),
    path("login/", views.login, name="login"),
    path("sign_up/", views.sign_up, name="sign_up"),
    path("instructor/", views.instructor_dashboard, name="instructor_dashboard"),
    path('course/add/', views.create_course, name='create_course'),
    path("course/<int:pk>/edit/", views.edit_course, name="edit_course"),
    path("course/<int:pk>/delete/", views.delete_course, name="delete_course"),
    path("student/", views.student_dashboard, name="student_dashboard"),
    path("enrollment/", views.enrolment_page, name="enrolment_page"),
    path("enroll/<int:course_id>/", views.enrol_course, name="enrol_course"),
]