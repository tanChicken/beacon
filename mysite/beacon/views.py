from django.shortcuts import render, redirect, get_object_or_404
from .models import Course, Lesson, StudentReadingListItem, StudentReadingListProgress, StudentProfile
from .forms import CourseForm, LessonDetailForm
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.db import transaction
from django.contrib.auth import get_user_model

# Create your views here.
def home(request):
    return render(request, "home.html", {"hide_sidebar": True})

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
                username=email,  
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password,
            )
            user.role = "STUDENT"
            user.save()

            profile, created = StudentProfile.objects.get_or_create(user=user)
            profile.title = title
            profile.save()

        messages.success(request, "Signup successful! Please log in.")
        return redirect("login")

    return render(request, "signup.html")

def student_dashboard(request):
    student = request.user
    enrolled = student.courses_enroling.all()
    available_courses = Course.objects.filter(status="active").exclude(students=student)
    
    return render(request, "student_dashboard.html", {
        "courses": enrolled,
        "available_courses": available_courses,
        "student": student
    })
    
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

    lessons = request.user.lessons.all()  

    return render(request, "student_lessons.html", {"lessons": lessons})

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
        lesson_titles = request.POST.getlist("lesson_title")  
        if form.is_valid():
            with transaction.atomic():
                course = form.save(commit=False)
                course.instructor = request.user
                course.credit_points = 30  
                course.save()

                for title in lesson_titles:
                    if title.strip():
                        Lesson.objects.create(course=course, designer=request.user, title=title)

            messages.success(request, "Course created successfully!")
            return redirect("course_detail", pk=course.pk)
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

    lessons = course.lessons.all()
    return render(request, "course_form.html", {
        "form": form,
        "action": "Update",
        "lessons": lessons,
        "read_only_lessons": True,
    })

@login_required
def delete_course(request, pk):
    course = get_object_or_404(Course, pk=pk, instructor=request.user)
    course.delete()
    messages.success(request, "Course deleted successfully!")
    return redirect("instructor_dashboard")

@login_required
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    lessons = course.lessons.all()

    students_progress = []
    for student in course.students.all():
        total_items = StudentReadingListItem.objects.filter(lesson__course=course).count()
        completed_items = StudentReadingListProgress.objects.filter(
            student=student, completed=True, item__lesson__course=course
        ).count()

        percent_complete = 0
        if total_items > 0:
            percent_complete = int((completed_items / total_items) * 100)

        students_progress.append({
            "student": student,
            "completed": completed_items,
            "total": total_items,
            "percent": percent_complete,
        })

    return render(request, "course_details.html", {
        "course": course,
        "form": CourseForm(instance=course),
        "lessons": lessons,
        "students_progress": students_progress,
    })

@login_required
def lesson_detail_edit(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk)

    if request.method == "POST":
        form = LessonDetailForm(request.POST, instance=lesson)
        if form.is_valid():
            form.save()

            for item in lesson.reading_items.all():
                key = f"reading_item_{item.id}"
                if key in request.POST:
                    item.title = request.POST[key]
                    item.save()

            new_items = request.POST.getlist("new_reading_item")
            for title in new_items:
                if title.strip():
                    StudentReadingListItem.objects.create(lesson=lesson, title=title.strip())

            messages.success(request, f"Lesson '{lesson.title}' updated successfully!")
            return redirect("course_detail", pk=lesson.course.pk)
    else:
        form = LessonDetailForm(instance=lesson)

    return render(request, "lesson_detail_edit.html", {
        "lesson": lesson,
        "lesson_form": form
    })

@login_required
def create_lesson(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk, instructor=request.user)

    if request.method == "POST":
        form = LessonDetailForm(request.POST)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.course = course
            lesson.designer = request.user
            lesson.save()
            messages.success(request, f"Lesson '{lesson.title}' created successfully!")
            return redirect('course_detail', pk=course.pk)
    else:
        form = LessonDetailForm()

    return render(request, 'create_lesson.html', {
        'form': form,
        'course': course,
        'action': 'Create'
    })

@login_required
def delete_lesson(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk, designer=request.user)
    course_pk = lesson.course.pk
    lesson.delete()
    messages.success(request, "Lesson deleted successfully!")
    return redirect("course_detail", pk=course_pk)