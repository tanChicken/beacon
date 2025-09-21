from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from .models import Classroom, Course, Lesson, StudentReadingListProgress, Student, StudentProfile, User, StudentReadingListItem, Instructor, InstructorProfile, Enrolment
from .forms import CourseForm, InstructorLoginForm, LessonDetailForm, StudentLoginForm, StudentSignupForm, ReadingItemForm, ClassroomForm, EditClassroomForm
from django.contrib import messages
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction

from .models import Course, Student, StudentProfile, User  # note: import Student & StudentProfile


def home(request):
    return render(request, "home.html", {"hide_sidebar": True})

def login_view(request):
    return render(request, "login.html", {"hide_sidebar": True})

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
        password = request.POST.get("password") or ""
        confirm = request.POST.get("confirm_password") or ""
        email = (request.POST.get("email") or "").strip().lower()
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
                email=email,
                password=password,
                role="STUDENT",
            )

            profile = user.studentprofile
            profile.title = title
            profile.first_name = first_name
            profile.last_name = last_name
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

    # Only allow enrollment in active courses that the student isn't already enrolled in
    course = get_object_or_404(Course, id=course_id, status="active")

    course.students.add(student)
    messages.success(request, f"You have enrolled in {course.title}!")
    return redirect("student_dashboard")

@login_required
def student_course_details(request,pk):
    course = get_object_or_404(Course, pk=pk)

    # optional: only allow enrolled students to view
    if not course.students.filter(pk=request.user.pk).exists():
        messages.error(request, "You are not enrolled in this course.")
        return redirect("student_dashboard")

    # lessons = getattr(course, "lessons", course.lesson_set).all()
    lessons = course.lessons.all()
    return render(request, "student_course_details.html", {"course": course, "lessons": lessons})

@login_required
def student_lessons(request):
    if not request.user.role == "STUDENT":
        return render(request, "403.html")

    lessons = request.user.lessons.all()  

    return render(request, "student_lessons.html", {"lessons": lessons})

@login_required()
def student_lesson_details(request, pk):    

    lesson = get_object_or_404(Lesson, pk=pk) 
    return render(request, "student_lesson_details.html", {"lesson": lesson})


@login_required
def student_classroom(request):
    classrooms = Classroom.objects.prefetch_related("lessons").all()
    return render(request, "student_classroom.html", {"classrooms": classrooms})

@login_required
def student_classroom_details(request, pk):
    classroom = get_object_or_404(Classroom, pk=pk)
    return render(request, 'student_classroom_details.html', {'classroom': classroom})


def instructor_login(request):
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        password = request.POST.get("password") or ""

        # Try authenticating with email as username first
        user = authenticate(request, username=email, password=password)

        if user is None:
            messages.error(request, "Invalid email or password.")
            # return render(request, "instructor_login.html", {"hide_sidebar": True})
        else:
            if getattr(user, "role", None) == "INSTRUCTOR":
                login(request, user)
                return redirect("instructor_dashboard")
            messages.error(request, "This account is not an instructor. Please use the student login.")
    return render(request, "instructor_login.html")

@login_required
def instructor_dashboard(request):
    # Get courses created by this instructor
    courses = Course.objects.filter(instructor=request.user)
    return render(request, "instructor_dashboard.html", {
        "courses": courses,
    })

@login_required
def create_course(request):
    if request.method == "POST":
        form = CourseForm(request.POST)
        lesson_titles = request.POST.getlist("lesson_title")  
        if form.is_valid():
            with transaction.atomic():
                course = form.save(commit=False)
                # course.instructor = request.user
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
            return redirect("instructor_dashboard")  # reloads page with updated info
    else:
        form = CourseForm(instance=course)

    return render(request, "course_form.html", {
        "form": form,
        "course": course,
        "action": "Edit",
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
    next_count = course.lessons.count() + 1
    next_lesson_id = f"L{next_count:03d}"

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

    return render(
        request, 'create_lesson.html',
        {
        'form': form,
        'course': course,
        'action': 'Create',
        'next_lesson_id': next_lesson_id,
    })

@login_required
def delete_lesson(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk, designer=request.user)
    course_pk = lesson.course.pk
    lesson.delete()
    messages.success(request, "Lesson deleted successfully!")
    return redirect("course_detail", pk=course_pk)

@login_required
def enrol_lesson(request, lesson_id):
    student = request.user
    lesson = get_object_or_404(Lesson, id=lesson_id)

    if Enrolment.objects.filter(student=student, lesson=lesson).exists():
        messages.warning(request, f"You are already enrolled in {lesson.title}.")
    else:
        Enrolment.objects.create(student=student, lesson=lesson)
        messages.success(request, f"You have enrolled in {lesson.title}!")

    return redirect("student_lesson_details", pk=lesson.id)
@login_required
def instructor_classroom(request):
    classrooms = Classroom.objects.prefetch_related("lessons").all()
    return render(request, "instructor_classroom.html", {
        "classrooms": classrooms,
    })

@login_required
def edit_classroom(request, pk):
    classroom = get_object_or_404(Classroom, pk=pk)

    # Authorization: only supervisor or instructors can edit
    # user = request.user
    # can_edit = (
    #     getattr(user, "role", None) == "INSTRUCTOR"
    #     or user == classroom.supervisor
    #     or user.has_perm("beacon.change_classroom")
    # )
    # if not can_edit:
    #     raise PermissionDenied("You do not have permission to edit this classroom.")

    if request.method == "POST":
        form = EditClassroomForm(request.POST, instance=classroom, request=request)
        if form.is_valid():
            form.save()
            messages.success(request, "Classroom updated successfully.")
            # Redirect wherever makes sense in your app:
            # - to details
            return redirect("student_classroom_details", pk=classroom.pk)
            # - or to list: return redirect("classroom_list")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = EditClassroomForm(instance=classroom, request=request)

    return render(request, "edit_classroom.html", {"classroom": classroom, "form": form})

@login_required
def create_classroom(request, pk=None):
    # ID, course ID, duration [2/3/4 weeks], classroom supervisor
    preselected_course = get_object_or_404(Course, pk=pk) if pk is not None else None

    if request.method == "POST":
        form = ClassroomForm(request.POST, request=request, preselected_course=preselected_course)
        if form.is_valid():
            classroom = form.save(commit=False)
            # If course dropdown was disabled, ensure we still set it
            if preselected_course:
                classroom.course_id = preselected_course
            classroom.save()
            messages.success(request, "Classroom created successfully.")
            return redirect("course_detail", pk=classroom.course_id.pk)  # adjust route name if different
    else:
        form = ClassroomForm(request=request, preselected_course=preselected_course)

    return render(request, "create_classroom.html", {"form": form, "course": preselected_course})

# @login_required
# def delete_classroom(request, pk):
#     from .models import Classroom

#     # Get classroom and ensure instructor owns the related course
#     classroom = get_object_or_404(Classroom, pk=pk, course_id__instructor=request.user)

#     if request.method == "POST":
#         # Count affected lessons before deletion
#         affected_lessons = classroom.lessons.all()
#         lesson_count = affected_lessons.count()

#         # Store classroom info for success message
#         classroom_info = f"Classroom {classroom.classroom_id}"

#         # Delete classroom (lessons will be automatically unassigned due to SET_NULL)
#         classroom.delete()

#         # Success message with lesson info
#         if lesson_count > 0:
#             messages.success(request, f"{classroom_info} deleted successfully! {lesson_count} lesson(s) unassigned from this classroom.")
#         else:
#             messages.success(request, f"{classroom_info} deleted successfully!")

#         return redirect("instructor_dashboard")

#     # GET request - show confirmation page
#     affected_lessons = classroom.lessons.all()
#     return render(request, "classroom_confirm_delete.html", {
#         "classroom": classroom,
#         "affected_lessons": affected_lessons,
#     })