from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from .models import Course
from .forms import CourseForm, InstructorLoginForm, StudentLoginForm, StudentSignupForm
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required

# Create your views here.
def home(request):
    return render(request, "home.html")

# Instructor

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

@login_required
def instructor_dashboard(request):
    courses = Course.objects.filter(instructor=request.user)
    return render(request, "instructor_dashboard.html", {"courses": courses})


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

@login_required
def student_dashboard(request):
    student = request.user
    enrolled = student.courses_enroling.all()  # Assuming ManyToManyField 'students'
    return render(request, "student_dashboard.html", {"courses": enrolled, "student": student})

@login_required
def enrolment_page(request):
    enrolled = request.user.enrolled_courses.all()
    available_courses = Course.objects.exclude(id__in=enrolled)
    return render(request, "enrolment.html", {"available_courses": available_courses})

@login_required
def enroll_course(request, pk):
    course = get_object_or_404(Course, pk=pk)
    user = request.user
    if user not in course.students.all():
        course.students.add(user)
        messages.success(request, f"You have successfully enrolled in {course.name}!")
    else:
        messages.info(request, f"You are already enrolled in {course.name}.")
    return redirect("student_dashboard")  # Replace with your dashboard URL name