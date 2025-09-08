from django.shortcuts import render, redirect, get_object_or_404
from .models import Course, Profile
from .forms import CourseForm
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.hashers import make_password

def home(request):
    return render(request, "home.html")

# ------------------------
# Signup view
# ------------------------
def sign_up(request):
    if request.method == "POST":
        email = request.POST["email"]
        first_name = request.POST["first_name"]
        last_name = request.POST["last_name"]
        title = request.POST.get("title")
        password = request.POST["password"]
        role = request.POST.get("role")  # 👈 capture role

        if User.objects.filter(username=email).exists():
            messages.error(request, "Email already registered.")
            return redirect("sign_up")

        user = User.objects.create(
            username=email,
            first_name=first_name,
            last_name=last_name,
            password=make_password(password)
        )
        Profile.objects.create(user=user, role=role)  # 👈 attach profile

        messages.success(request, "Account created! Please log in.")
        return redirect("login")

    return render(request, "signup.html")

# ------------------------
# Login view
# ------------------------
def login_view(request):
    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]

        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            if user.profile.role == "student":
                return redirect("student_dashboard")
            else:
                return redirect("instructor_dashboard")
        else:
            messages.error(request, "Invalid email or password.")
            return redirect("login")

    return render(request, "login.html")

# ------------------------
# Instructor dashboard
# ------------------------
def instructor_dashboard(request):
    courses = Course.objects.all()
    return render(request, "instructor_dashboard.html", {"courses": courses})

# ------------------------
# Student dashboard
# ------------------------
def student_dashboard(request):
    student = request.user
    enrolled = student.courses_enroling.all() if student.is_authenticated else []
    return render(request, "student_dashboard.html", {"courses": enrolled, "student": student})

def enrolment_page(request):
    student = request.user
    available_courses = Course.objects.filter(status="active").exclude(students=student)
    return render(request, "enrolment.html", {"available_courses": available_courses, "student": student})

def enrol_course(request, course_id):
    student = request.user
    course = get_object_or_404(Course, id=course_id)
    course.students.add(student)
    messages.success(request, f"You have enrolled in {course.title}!")
    return redirect("student_dashboard")

# ------------------------
# Course CRUD
# ------------------------
def create_course(request):
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.instructor = request.user
            course.save()
            messages.success(request, "Course created successfully!")
            return redirect("instructor_dashboard")
    else:
        form = CourseForm()
    return render(request, "course_form.html", {"form": form, "action": "Create"})

def edit_course(request, pk):
    course = get_object_or_404(Course, pk=pk, instructor=request.user)
    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "Course updated successfully!")
            return redirect("instructor_dashboard")
    else:
        form = CourseForm(instance=course)
    return render(request, "course_form.html", {"form": form, "action": "Update"})

def delete_course(request, pk):
    course = get_object_or_404(Course, pk=pk, instructor=request.user)
    if request.method == "POST":
        course.delete()
        messages.success(request, "Course deleted successfully!")
        return redirect("instructor_dashboard")
    return render(request, "course_confirm_delete.html", {"course": course})

def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    return render(request, "course_details.html", {"course": course})