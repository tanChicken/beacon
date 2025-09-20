from django.shortcuts import render, redirect, get_object_or_404
from .models import Course, Lesson, StudentReadingListItem, StudentReadingListProgress, StudentProfile
from .forms import CourseForm, LessonDetailForm, ReadingItemForm
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.db import transaction
from django.contrib.auth import get_user_model
from django.forms import inlineformset_factory
from django.db.models import Count

from .models import Course, Student, StudentProfile, User  # note: import Student & StudentProfile


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

def student_dashboard(request):
    student = request.user
    enrolled = student.courses_enroling.all()
    
    # Get courses not yet enrolled by this student
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

@login_required
def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    reading_items = lesson.reading_items.all()

    # Check if student is enrolled in this lesson
    is_enrolled = request.user in lesson.enrolled_students.all()

    # Check if student is enrolled in the course (prerequisite for lesson enrollment)
    can_enroll = False
    if lesson.course and request.user.role == "STUDENT":
        can_enroll = request.user in lesson.course.students.all()

    if request.method == "POST" and request.user.is_authenticated:
        # Handle lesson enrollment
        if 'enroll_lesson' in request.POST and can_enroll and not is_enrolled:
            lesson.enrolled_students.add(request.user)
            messages.success(request, f"You have enrolled in {lesson.title}!")
            return redirect("lesson_detail", lesson_id=lesson.id)

        # Handle lesson unenrollment
        elif 'unenroll_lesson' in request.POST and is_enrolled:
            lesson.enrolled_students.remove(request.user)
            messages.success(request, f"You have unenrolled from {lesson.title}!")
            return redirect("lesson_detail", lesson_id=lesson.id)

        # Handle reading list progress (only if enrolled)
        elif is_enrolled:
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
        "is_enrolled": is_enrolled,
        "can_enroll": can_enroll,
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
        lesson_titles = request.POST.getlist("lesson_title")  # grab all lessons

        if form.is_valid():
            with transaction.atomic():
                course = form.save(commit=False)
                course.instructor = request.user
                course.credit_points = 30  # fixed
                course.save()

                # save each lesson
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
    lesson = get_object_or_404(Lesson, pk=pk, course__instructor=request.user)

    # Lesson main form
    lesson_form = LessonDetailForm(request.POST or None, instance=lesson)

    # Reading list formset
    ReadingFormSet = inlineformset_factory(
        Lesson, StudentReadingListItem, form=ReadingItemForm, extra=1, can_delete=True
    )
    reading_formset = ReadingFormSet(request.POST or None, instance=lesson)

    # Get students enrolled in the course for enrollment options
    course_students = lesson.course.students.all() if lesson.course else []
    enrolled_students = lesson.enrolled_students.all()

    if request.method == "POST":
        # Handle student enrollment
        if 'enroll_student' in request.POST:
            student_id = request.POST.get('student_id')
            if student_id:
                student = get_object_or_404(User, id=student_id)
                lesson.enrolled_students.add(student)
                messages.success(request, f"{student.username} enrolled in lesson successfully!")
                return redirect("lesson_detail_edit", pk=lesson.pk)

        # Handle student unenrollment
        elif 'unenroll_student' in request.POST:
            student_id = request.POST.get('student_id')
            if student_id:
                student = get_object_or_404(User, id=student_id)
                lesson.enrolled_students.remove(student)
                messages.success(request, f"{student.username} unenrolled from lesson successfully!")
                return redirect("lesson_detail_edit", pk=lesson.pk)

        # Handle lesson form and reading list updates
        elif lesson_form.is_valid() and reading_formset.is_valid():
            lesson_form.save()
            reading_formset.save()

            # Add new reading items
            new_items = request.POST.getlist("new_reading_item")
            for title in new_items:
                if title.strip():
                    StudentReadingListItem.objects.create(lesson=lesson, title=title.strip())

            messages.success(request, f"Lesson '{lesson.title}' updated successfully!")
            return redirect("lesson_detail_edit", pk=lesson.pk)

    return render(request, "lesson_detail_edit.html", {
        "lesson": lesson,
        "lesson_form": lesson_form,
        "reading_formset": reading_formset,
        "enrolled_students": enrolled_students,
        "course_students": course_students,
    })

@login_required
def delete_lesson(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk, designer=request.user)
    course_pk = lesson.course.pk

    # Delete immediately
    lesson.delete()
    messages.success(request, "Lesson deleted successfully!")
    return redirect("course_detail", pk=course_pk)