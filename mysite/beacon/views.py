from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction

from .models import Course, StudentProfile, TeacherProfile
from .forms import CourseForm


def home(request):
    return render(request, "home.html", {"hide_sidebar": True})


# ------------------------
# Login
# ------------------------
def login_view(request):
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        password = request.POST.get("password") or ""

        user = authenticate(request, username=email, password=password)

        if not user:
            messages.error(request, "Invalid email or password.")
            return render(request, "login.html")

        # Login first
        login(request, user)

        # Redirect automatically based on role/profile
        if hasattr(user, "profile"):
            role = user.profile.role.upper()
            if role == "STUDENT":
                return redirect("student_dashboard")
            elif role == "INSTRUCTOR":
                return redirect("instructor_dashboard")
            else:
                messages.error(request, "This account is not a student. Please use the instructor login.")
    return render(request, "login.html", {"hide_sidebar": True})


# ------------------------
# Student Signup
# ------------------------
def student_signup(request):
    if request.method == "POST":
        first = (request.POST.get("first_name") or "").strip()
        last = (request.POST.get("last_name") or "").strip()
        student_id = (request.POST.get("title") or "").strip()  # renamed for clarity
        email = (request.POST.get("email") or "").strip().lower()
        password = request.POST.get("password") or ""

        if not first or not last or not student_id or not email or not password:
            messages.error(request, "Please fill in all fields.")
            return render(request, "signup.html")

        UserModel = get_user_model()
        if UserModel.objects.filter(email=email).exists():
            messages.error(request, "This email is already registered.")
            return render(request, "signup.html")

        with transaction.atomic():
            # Create the user
            user = UserModel.objects.create_user(
                username=email,
                email=email,
                first_name=first,
                last_name=last,
                password=password,
            )

            # Assign role via Profile
            if hasattr(user, "profile"):
                user.profile.role = "student"
                user.profile.save()

            # Create StudentProfile
            StudentProfile.objects.create(user=user, student_id=student_id)

        messages.success(request, "Signup successful! Please log in.")
        return redirect("login")

    # GET → show the page
    return render(request, "signup.html", {"hide_sidebar": True})


# ------------------------
# Instructor Signup
# ------------------------
def instructor_signup(request):
    if request.method == "POST":
        first = (request.POST.get("first_name") or "").strip()
        last = (request.POST.get("last_name") or "").strip()
        email = (request.POST.get("email") or "").strip().lower()
        password = request.POST.get("password") or ""

        user = authenticate(request, username=email, password=password)
        if user is None:
            messages.error(request, "Invalid email or password.")
        else:
            if getattr(user, "role", None) == "TEACHER":
                login(request, user)
                return redirect("instructor_dashboard")
            messages.error(request, "This account is not an instructor. Please use the student login.")
            return render(request, "instructor_login.html") 

        UserModel = get_user_model()
        if UserModel.objects.filter(email=email).exists():
            messages.error(request, "This email is already registered.")
            return render(request, "signup.html")

        with transaction.atomic():
            # Create the user
            user = UserModel.objects.create_user(
                username=email,
                email=email,
                first_name=first,
                last_name=last,
                password=password,
            )

            # Assign role via Profile
            if hasattr(user, "profile"):
                user.profile.role = "instructor"
                user.profile.save()

            # Create TeacherProfile
            TeacherProfile.objects.create(user=user)

        messages.success(request, "Instructor signup successful! Please log in.")
        return redirect("login")

    return render(request, "signup.html", {"hide_sidebar": True})


# ------------------------
# Dashboards
# ------------------------
@login_required
def student_dashboard(request):
    if not request.user.is_authenticated:
        return redirect("login")

    courses = Course.objects.filter(students=request.user)

    return render(request, "student_dashboard.html", {
        "courses": courses,
    })


@login_required
def instructor_dashboard(request):
    return render(request, "instructor_dashboard.html")


# ------------------------
# Courses (Instructor only)
# ------------------------
@login_required
def create_course(request):
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.instructor = request.user
            course.save()
            messages.success(request, "Course created successfully.")
            return redirect("instructor_dashboard")
    else:
        form = CourseForm()
    return render(request, "create_course.html", {"form": form})


@login_required
def edit_course(request, pk):
    course = get_object_or_404(Course, pk=pk, instructor=request.user)
    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "Course updated successfully.")
            return redirect("instructor_dashboard")
    else:
        form = CourseForm(instance=course)
    return render(request, "edit_course.html", {"form": form})


@login_required
def delete_course(request, pk):
    course = get_object_or_404(Course, pk=pk, instructor=request.user)
    if request.method == "POST":
        course.delete()
        messages.success(request, "Course deleted.")
        return redirect("instructor_dashboard")
    return render(request, "delete_course.html", {"course": course})


# ------------------------
# Enrollment (Students)
# ------------------------
@login_required
def enrolment_page(request):
    courses = Course.objects.filter(status="active")
    return render(request, "enrolment.html", {"available_courses": courses})


@login_required
def enrol_course(request, course_id):
    course = get_object_or_404(Course, id=course_id, status="active")
    if not hasattr(request.user, "profile") or request.user.profile.role.upper() != "STUDENT":
        messages.error(request, "Only students can enroll in courses.")
        return redirect("home")

    course.students.add(request.user)
    messages.success(request, f"You have enrolled in {course.title}.")
    return redirect("student_dashboard")


@login_required
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    return render(request, "course_detail.html", {"course": course})