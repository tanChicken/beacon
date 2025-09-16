from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from .models import Course, Lesson, StudentReadingListProgress
from .forms import CourseForm, InstructorLoginForm, StudentLoginForm, StudentSignupForm
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction, IntegrityError
from django.contrib.auth import get_user_model

from .models import Course, Student, StudentProfile  # note: import Student & StudentProfile


# Create your views here.
def home(request):
    return render(request, "home.html", {"hide_sidebar": True})


# ------------------------
# Login
# ------------------------
def login_view(request):
    return render(request, "home.html", {"hide_sidebar": True})

def student_login(request):
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        password = request.POST.get("password") or ""

        user = authenticate(request, username=email, password=password)
        if user is None:
            messages.error(request, "Invalid email or password.")
        else:
            # allow only Student accounts here
            if getattr(user, "role", None) == "STUDENT":
                login(request, user)
                return redirect("student_dashboard")
            else:
                messages.error(request, "This account is not a student. Please use the instructor login.")
    return render(request, "login.html")

def student_signup(request):
    if request.method == "POST":
        first_name = (request.POST.get("first_name") or "").strip()
        last_name = (request.POST.get("last_name") or "").strip()
        email = (request.POST.get("email") or "").strip().lower()
        password = request.POST.get("password") or ""
        confirm = request.POST.get("confirm_password") or ""
        title = request.POST.get("title") or ""  

        if not first_name or not last_name or not email or not password or not confirm or not title:
            messages.error(request, "Please fill in all fields.")
            return render(request, "signup.html")

        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return render(request, "signup.html")

        UserModel = get_user_model()
        if UserModel.objects.filter(email=email).exists():
            messages.error(request, "This email is already registered.")
            return render(request, "signup.html")


        with transaction.atomic():
            user = UserModel.objects.create_user(
                username=email,  # keep if your model still uses username
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password,
            )
            # set role
            user.role = "STUDENT"
            user.save()

            # ensure profile exists, now set title
            profile, created = StudentProfile.objects.get_or_create(user=user)
            profile.title = title
            profile.save()

        messages.success(request, "Signup successful! Please log in.")
        return redirect("login")

    return render(request, "signup.html")


@login_required(login_url="/login/")
def student_dashboard(request):
    student = request.user
    enrolled = student.courses_enroling.all()  # Assuming ManyToManyField 'students'
    return render(request, "student_dashboard.html", {"courses": enrolled, "student": student})

@login_required
def enrolment_page(request):
    student = request.user
    available_courses = Course.objects.filter(status="active").exclude(students=student)
    return render(request, "enrolment.html", {"available_courses": available_courses, "student": student})

@login_required
def enrol_course(request, course_id):
    student = request.user
    course = get_object_or_404(Course, id=course_id)
    course.students.add(student)
    messages.success(request, f"You have enrolled in {course.title}!")
    return redirect("student_dashboard")

@login_required
def student_lessons(request):
    if not request.user.role == "STUDENT":
        return render(request, "403.html")

    lessons = request.user.lessons.all()  # thanks to the ManyToManyField

    return render(request, "student_lessons.html", {"lessons": lessons})

@login_required
def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    reading_items = lesson.reading_items.all()

    if request.method == "POST" and request.user.is_authenticated:
        for item in reading_items:
            checkbox = str(item.id) in request.POST
            progress, created = StudentReadingListProgress.objects.get_or_create(
                student=request.user, item=item
            )
            progress.completed = checkbox
            progress.save()
        return redirect("lesson_detail", lesson_id=lesson.id)

    completed_ids = list(
    StudentReadingListProgress.objects
        .filter(student=request.user, item__lesson=lesson, completed=True)
        .values_list('item_id', flat=True)
)

    return render(request, "lesson_detail.html", {
        "lesson": lesson,
        "reading_items": reading_items,
        "progress": completed_ids,
    })

def instructor_login(request):
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        password = request.POST.get("password") or ""

        user = authenticate(request, username=email, password=password)
        if user is None:
            messages.error(request, "Invalid email or password.")
        else:
            if getattr(user, "role", None) == "INSTRUCTOR":
                login(request, user)
                return redirect("instructor_dashboard")
            messages.error(request, "This account is not an instructor. Please use the student login.")
    return render(request, "instructor_login.html")

@login_required(login_url="/i_login/")
def instructor_dashboard(request):
    courses = Course.objects.filter(instructor=request.user)
    return render(request, "instructor_dashboard.html", {"courses": courses})

@login_required
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

@login_required
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

@login_required
def delete_course(request, pk):
    course = get_object_or_404(Course, pk=pk, instructor=request.user)
    if request.method == "POST":
        course.delete()
        messages.success(request, "Course deleted successfully!")
        return redirect("instructor_dashboard")
    return render(request, "course_confirm_delete.html", {"course": course})

@login_required
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    return render(request,"course_details.html", {"course":course})
