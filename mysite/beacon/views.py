from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from .models import Course
from .forms import CourseForm, InstructorLoginForm, StudentLoginForm, StudentSignupForm
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required

# Create your views here.
def home(request):
    return render(request, "home.html")

def login(request):
    return render(request, "login.html")

def sign_up(request):
    return render(request, "signup.html")

def instructor_dashboard(request):
    courses = Course.objects.filter(instructor=request.user)
    return render(request, "instructor_dashboard.html", {"courses": courses})

def i_login(request):
    return render(request, "blank.html")

# Mock user data
MOCK_USERS = [
    {"email": "test", "password": "1234"},
    {"email": "hi", "password": "abcd"}
]

def student_login(request):
    if request.method == "POST":
        form = StudentLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            # Authenticate user
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)  # Start session
                return redirect("student_dashboard")
            else:
                messages.error(request, "Invalid email or password.")
    else:
        form = StudentLoginForm()

    return render(request, "login.html", {"form": form})

def student_signup(request):
    if request.method == "POST":
        form = StudentSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = form.cleaned_data['email']  # use email as username
            user.set_password(form.cleaned_data['password'])  # hash password
            user.save()
            messages.success(request, "Signup successful! Please log in.")
            return redirect("login")  # redirect to your login page
    else:
        form = StudentSignupForm()
    return render(request, "signup.html", {"form": form})

def instructor_login(request):
    if request.method == "POST":
        form = InstructorLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            # Authenticate user
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)  # Start session
                return redirect("instructor_dashboard")
            else:
                messages.error(request, "Invalid email or password.")
    else:
        form = InstructorLoginForm()

    return render(request, "login.html", {"form": form})


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
    dummy_instructor = User.objects.first()
    if not dummy_instructor:
        dummy_instructor = User.objects.create(username="test_instructor")

    course = get_object_or_404(Course, pk=pk, instructor=dummy_instructor)

    if request.method == "POST":
        course.delete()
        messages.success(request, "Course deleted successfully!")
        return redirect("instructor_dashboard")

    return render(request, "course_confirm_delete.html", {"course": course})

#@login_required
def student_dashboard(request):
    student = request.user
    enrolled = student.courses_enroling.all()  # Assuming ManyToManyField 'students'
    return render(request, "student_dashboard.html", {"courses": enrolled, "student": student})


def enrolment_page(request):
    dummy_student, created = User.objects.get_or_create(username="test_student")
    # Only show active courses not already enrolled
    available_courses = Course.objects.filter(status="active").exclude(students=dummy_student)
    return render(request, "enrolment.html", {"available_courses": available_courses, "student": dummy_student})

def enrol_course(request, course_id):
    dummy_student, created = User.objects.get_or_create(username="test_student")
    course = get_object_or_404(Course, id=course_id)
    course.students.add(dummy_student)
    messages.success(request, f"You have enrolled in {course.title}!")
    return redirect("student_dashboard")

def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    return render(request, "course_details.html", {"course": course})

