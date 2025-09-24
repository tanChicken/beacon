from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from .models import Classroom, Course, Lesson, StudentChecklistProgress, Student, StudentProfile, User, StudentChecklistItem, Instructor, InstructorProfile, Enrolment
from .forms import CourseForm, InstructorLoginForm, LessonDetailForm, StudentLoginForm, StudentSignupForm, ClassroomForm, EditClassroomForm, LessonTaskFormSet
from django.contrib import messages
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction

from .models import Course, Student, StudentProfile, User
from django.db import models

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
def unenrol_course(request, pk):
    course = get_object_or_404(Course, pk=pk)
    student = request.user
    
    # remove the student from the course enrolments
    if course.students.filter(id=student.id).exists():
        course.students.remove(student)
    
    return redirect("student_dashboard")  


@login_required
def student_course_details(request,pk):
    course = get_object_or_404(Course, pk=pk)
    lessons = Lesson.objects.filter(course=course)

    lesson_status = []
    for lesson in lessons:
        enrolment = Enrolment.objects.filter(student=request.user, lesson=lesson).first()
        completed = enrolment.completed if enrolment else False
        enrolled = enrolment is not None and not completed
        prereqs = lesson.prerequisites.all()

        missing = [p for p in prereqs if not Enrolment.objects.filter(student=request.user, lesson=p, completed=True).exists()]
        prereqs_met = (len(missing) == 0)

        can_enroll = prereqs_met and not enrolled and not completed
        lesson_status.append(
            {
                "lesson": lesson,
                "enrolled": enrolled,
                "can_enroll": can_enroll,
                "missing_prereqs": missing,
                "completed" : completed,
            }
        )
    
    # Sort by a custom key
    lesson_status_sorted = sorted(
        lesson_status,
        key=lambda s: (
            # Use numbers so lower comes first
            0 if s["completed"] else 1 if s["enrolled"] else 2 if s["can_enroll"] else 3
        )
    )

    return render(request, "student_course_details.html", {
        "course": course,
        "lesson_status": lesson_status_sorted,
    })

@login_required
def student_lessons(request):
    if not request.user.role == "STUDENT":
        return render(request, "403.html")

    lessons = request.user.lessons.all()  

    return render(request, "student_lessons.html", {"lessons": lessons})

@login_required()
def student_lesson_details(request, pk):    

    lesson = get_object_or_404(Lesson, pk=pk)
    student = request.user  

    # Check if already enrolled
    enrolment_obj = Enrolment.objects.filter(student=student, lesson=lesson).first()
    is_enrolled = enrolment_obj is not None and not enrolment_obj.completed
    is_completed = enrolment_obj.completed if enrolment_obj else False

    # Check prerequisites
    prereqs = lesson.prerequisites.all()
    missing_prereqs = [
        p for p in prereqs
        if not Enrolment.objects.filter(student=student, lesson=p, completed=True).exists()
    ]
    prereqs_met = (len(missing_prereqs) == 0)

    can_enroll = (
        lesson.course in student.courses_enroling.all()
        and not is_enrolled
        and prereqs_met
    )

    return render(request, "student_lesson_details.html", {
        "lesson": lesson,
        "is_enrolled": is_enrolled,
        "can_enroll": can_enroll,
        "missing_prereqs": missing_prereqs,  # optional: useful to show in template
        "is_completed": is_completed,
    })



@login_required
def student_classroom(request):
    # classrooms = Classroom.objects.prefetch_related("lessons").all()
    # classrooms = Classroom.objects.filter(...).exclude(students=student)
    student = request.user
    classrooms = (
        Classroom.objects
        .select_related("course_id")          # FK field name is course_id
        .prefetch_related("lessons")
        .filter(course_id__students=student)  # <-- traverse via course_id
        .distinct()
    )
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
    courses = (
        Course.objects.filter(instructor=request.user)
        .order_by("status", "title") 
    )
    return render(request, "instructor_dashboard.html", {"courses": courses})

@login_required
def create_course(request):
    if request.method == "POST":
        form = CourseForm(request.POST)
        lesson_titles = request.POST.getlist("lesson_title")  
        if form.is_valid():
            with transaction.atomic():
                course = form.save(commit=False)
                course.save()

                for title in lesson_titles:
                    if title.strip():
                        Lesson.objects.create(course=course, designer=request.user, title=title, objective='', assignment='')

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
    classrooms = Classroom.objects.filter(course_id=course)

    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)

        if form.is_valid():
            form.save()  # <-- actually save course changes
            messages.success(request, "Course updated successfully!")

        # Handle new inline lessons
        new_titles = request.POST.getlist("new_lesson_title")
        for title in new_titles:
            if title.strip():
                Lesson.objects.create(
                    course=course,
                    title=title.strip(),
                    designer=request.user,
                    lesson_point=0,
                    status="DRAFT"
                )
        if new_titles:
            messages.success(request, f"{len(new_titles)} lesson(s) added successfully!")

        return redirect("instructor_dashboard")

    else:
        form = CourseForm(instance=course)

    # Student progress
    students_progress = []
    for student in course.students.all():
        total_items = StudentChecklistItem.objects.filter(lesson__course=course).count()
        completed_items = StudentChecklistProgress.objects.filter(
            student=student, completed=True, item__lesson__course=course
        ).count()
        percent_complete = int((completed_items / total_items) * 100) if total_items > 0 else 0

        students_progress.append({
            "student": student,
            "completed": completed_items,
            "total": total_items,
            "percent": percent_complete,
        })

    return render(request, "course_details.html", {
        "course": course,
        "form": form,
        "lessons": lessons,
        "classrooms": classrooms,
        "students_progress": students_progress,
    })

from django.db.models import Sum

@login_required
def lesson_detail_edit(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk)
    course = lesson.course
    available_classrooms = Classroom.objects.filter(course_id=course).order_by("classroom_id")

    # Always calculate totals for the whole course
    lessons = course.lessons.all()
    total_points = lessons.aggregate(total=Sum("lesson_point"))["total"] or 0
    remaining_points = 30 - total_points
    enrolments = Enrolment.objects.filter(lesson=lesson).select_related("student")
    enrolled_students = [enr.student for enr in enrolments]

    if request.method == "POST":
        form = LessonDetailForm(request.POST, instance=lesson, course=course, request=request)
        formset = LessonTaskFormSet(request.POST, instance=lesson)

        if form.is_valid() and formset.is_valid():
            lesson = form.save()
            formset.instance = lesson
            formset.save()

            # Update existing Reading Items
            for item in lesson.checklist_items.filter(item_type="READING"):
                key = f"reading_item_{item.id}"
                if key in request.POST:
                    item.title = request.POST[key]
                    item.save()

            # --- Add new reading items ---
            new_readings = request.POST.getlist("new_reading_item")
            for title in new_readings:
                if title.strip():
                    StudentChecklistItem.objects.create(
                        lesson=lesson,
                        title=title.strip(),
                        item_type="READING"
                    )
            
            # Update existing Assignments
            for item in lesson.checklist_items.filter(item_type="ASSIGNMENT"):
                key = f"assignment_item_{item.id}"
                if key in request.POST:
                    item.title = request.POST[key]
                    item.save()

            # --- Add new assignment items ---
            new_assignments = request.POST.getlist("new_assignment_item")
            for title in new_assignments:
                if title.strip():
                    StudentChecklistItem.objects.create(
                        lesson=lesson,
                        title=title.strip(),
                        item_type="ASSIGNMENT"
                    )
            total_points = course.lessons.aggregate(total=Sum("lesson_point"))["total"] or 0
            remaining_points = 30 - total_points

            messages.success(request, f"Lesson '{lesson.title}' updated successfully!")
    else:
        form = LessonDetailForm(instance=lesson, course=course, request=request)
        formset = LessonTaskFormSet(instance=lesson)

    # get all enrolments for this lesson
    enrolments = lesson.enrolments.all()

    # get all students (as User instances)
    students = [enrol.student for enrol in enrolments]
    # Student progress
    students_progress = []
    for student in students:
        total_items = StudentChecklistItem.objects.filter(lesson__course=course).count()
        completed_items = StudentChecklistProgress.objects.filter(
            student=student, completed=True, item__lesson__course=course
        ).count()
        percent_complete = int((completed_items / total_items) * 100) if total_items > 0 else 0

        students_progress.append({
            "student": student,
            "completed": completed_items,
            "total": total_items,
            "percent": percent_complete,
        })

    reading_items = lesson.checklist_items.filter(item_type="READING")
    assignment_items = lesson.checklist_items.filter(item_type="ASSIGNMENT")

    return render(request, "lesson_detail_edit.html", {
        "lesson": lesson,
        "lesson_form": form,
        "formset": formset,
        "course": course,
        "empty_form": formset.empty_form,
        "available_classrooms": available_classrooms,
        "total_points": total_points,
        "remaining_points": remaining_points,
        "enrolled_students": enrolled_students, 
        "students_progress": students_progress,
        "reading_items": reading_items,
        "assignment_items": assignment_items,
    })

@login_required
def create_lesson(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk, instructor=request.user)

    if request.method == "POST":
        form = LessonDetailForm(request.POST, course=course) 
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.course = course
            lesson.designer = request.user
            lesson.save()
            form.save_m2m()
            messages.success(request, f"Lesson '{lesson.title}' created successfully!")
            return redirect('course_detail', pk=course.pk)
    else:
        form = LessonDetailForm(course=course) 

    return render(
        request, 'create_lesson.html', 
        {
            'form': form, 
            'course': course, 
            'action': 'Create',
        }
    )

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

    missing = []
    for prereq in lesson.prerequisites.all():
        if not Enrolment.objects.filter(student=student, lesson=prereq).exists():
            missing.append(prereq)

    if missing:
        missing_ids = ", ".join(str(p.id) for p in missing)
        missing_titles = ", ".join(p.title for p in missing)

        messages.error(
            request,
            f"You must complete prerequisite lessons first. "
            f"Missing: {missing_titles} (IDs: {missing_ids})"
        )
        return redirect("student_course_details", course_id=lesson.course.id)

    Enrolment.objects.get_or_create(student=student, lesson=lesson)
    messages.success(request, f"You are now enrolled in {lesson.title}.")
    return redirect("student_lesson_details", pk=lesson.id)

@login_required
def unenrol_lesson(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk)
    student = request.user
    
    enrolment = Enrolment.objects.filter(student=student, lesson=lesson, completed=False).first()
    if enrolment:
        enrolment.delete()  
    return redirect("student_course_details", pk=lesson.course.pk)

@login_required
def instructor_classroom(request):
    instructor = request.user
    classrooms = (
        Classroom.objects
        .select_related("course_id")
        .prefetch_related("lessons")
        .filter(course_id__instructor=instructor)   # 🔑 only classrooms whose course is taught by this instructor
        .distinct()
    )

    return render(request, "instructor_classroom.html", {
        "classrooms": classrooms,
    })

@login_required
def edit_classroom(request, pk):
    classroom = get_object_or_404(Classroom, pk=pk)
    if request.method == "POST":
        form = EditClassroomForm(request.POST, instance=classroom, request=request)
        if form.is_valid():
            form.save()
            messages.success(request, "Classroom updated successfully.")
            return redirect("instructor_classroom")

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

@login_required
def delete_classroom(request, pk):
    classroom = get_object_or_404(Classroom, pk=pk)
    course_pk = classroom.course_id.pk   
    
    if request.method == "POST":  
        classroom.delete()
        messages.success(request, "Classroom deleted successfully!")
        return redirect("course_detail", pk=course_pk)
