from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name='home'),
    path("create_edit_courses/", views.create_edit_course, name="create or edit courses"),
    path("login/", views.login, name="Login"),
    path("sign_up/", views.sign_up, name="Sign Up")
]