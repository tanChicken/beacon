from django.shortcuts import render, redirect, get_object_or_404
from .models import Classroom, Course, Lesson, StudentChecklistProgress, StudentChecklistItem, Enrolment
from .forms import CourseForm, LessonDetailForm, ClassroomForm, EditClassroomForm, LessonTaskFormSet, StudentProfile, StudentPasswordChangeForm
from django.contrib import messages
from django.contrib.auth import authenticate, login, get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from.authz import role_required
from django.db.models import Sum

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
    
@role_required("STUDENT")
def enrolment_page(request):
    student = request.user
    available_courses = Course.objects.filter(status="active").exclude(students=student)
    return render(request, "enrolment.html", {"available_courses": available_courses, "student": student})

@role_required("STUDENT")
def enrol_course(request, course_id):
    student = request.user

    # Only allow enrollment in active courses that the student isn't already enrolled in
    course = get_object_or_404(Course, id=course_id, status="active")

    course.students.add(student)
    messages.success(request, f"You have enrolled in {course.title}!")
    return redirect("student_dashboard")

@role_required("STUDENT")
def unenrol_course(request, pk):
    course = get_object_or_404(Course, pk=pk)
    student = request.user
    
    # remove the student from the course enrolments
    if course.students.filter(id=student.id).exists():
        course.students.remove(student)
    
    return redirect("student_dashboard")  


@role_required("STUDENT")
def student_course_details(request,pk):
    course = get_object_or_404(Course, pk=pk)
    lessons = Lesson.objects.filter(course=course, status="PUBLISHED")

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

@role_required("STUDENT")
def student_lessons(request):
    if not request.user.role == "STUDENT":
        return render(request, "403.html")

    lessons = request.user.lessons.all()  

    return render(request, "student_lessons.html", {"lessons": lessons})

@role_required("STUDENT")
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

    completed_item_ids = StudentChecklistProgress.objects.filter(
        student=student, completed=True, item__lesson=lesson
    ).values_list("item_id", flat=True)

    return render(request, "student_lesson_details.html", {
        "lesson": lesson,
        "is_enrolled": is_enrolled,
        "can_enroll": can_enroll,
        "missing_prereqs": missing_prereqs,  # optional: useful to show in template
        "is_completed": is_completed,
        "completed_item_ids": list(completed_item_ids),
    })

@login_required
def toggle_checklist_item(request, item_id):
    item = get_object_or_404(StudentChecklistItem, id=item_id)
    student = request.user
    lesson = item.lesson

    progress, _ = StudentChecklistProgress.objects.get_or_create(
        student=student,
        item=item,
    )

    progress.completed = not progress.completed
    progress.save()

    total_items = StudentChecklistItem.objects.filter(lesson=lesson).count()
    completed_items = StudentChecklistProgress.objects.filter(
        student=student, item__lesson=lesson, completed=True
    ).count()

    if total_items > 0 and total_items == completed_items:
        # Student finished all checklist items → mark enrolment completed
        enrolment, _ = Enrolment.objects.get_or_create(student=student, lesson=lesson)
        enrolment.completed = True
        enrolment.credit_earned = lesson.lesson_point  # award credits
        enrolment.save()
    else:
        # If not fully complete, keep enrolment but reset completion/credits
        enrolment = Enrolment.objects.filter(student=student, lesson=lesson).first()
        if enrolment:
            enrolment.completed = False
            enrolment.credit_earned = 0
            enrolment.save()

    return JsonResponse({"completed": progress.completed})

@role_required("STUDENT")
def student_classroom(request):
    student = request.user
    classrooms = (
        Classroom.objects
        .select_related("course_id")          # FK field name is course_id
        .prefetch_related("lessons")
        .filter(course_id__students=student)  # <-- traverse via course_id
        .distinct()
    )
    return render(request, "student_classroom.html", {"classrooms": classrooms})

@role_required("STUDENT")
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

@role_required("INSTRUCTOR")
def instructor_dashboard(request):
    courses = (
        Course.objects.filter(instructor=request.user)
        .order_by("status", "title") 
    )
    return render(request, "instructor_dashboard.html", {"courses": courses})

@role_required("INSTRUCTOR")
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

@role_required("INSTRUCTOR")
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

@role_required("INSTRUCTOR")
def delete_course(request, pk):
    course = get_object_or_404(Course, pk=pk, instructor=request.user)
    course.delete()
    messages.success(request, "Course deleted successfully!")
    return redirect("instructor_dashboard")

@role_required("INSTRUCTOR")
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

        return redirect("course_detail", pk=course.pk)  # reloads page with updated info

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

@role_required("INSTRUCTOR")
def lesson_detail_edit(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk)
    course = lesson.course
    available_classrooms = Classroom.objects.filter(course_id_id=course.pk).order_by("classroom_id")

    total_points = course.lessons.aggregate(total=Sum("lesson_point"))["total"] or 0
    remaining_points = 30 - total_points

    if request.method == "POST":
        # Main lesson form
        form = LessonDetailForm(request.POST, instance=lesson, course=course, request=request)

        # Formset for lesson tasks
        formset = LessonTaskFormSet(request.POST, instance=lesson)

        if form.is_valid() and formset.is_valid():
            # Save lesson
            lesson = form.save()

            # Save tasks
            formset.instance = lesson
            formset.save()

            # Update existing reading items
            for item in lesson.checklist_items.filter(item_type="READING"):
                key = f"reading_item_{item.id}"
                if key in request.POST:
                    item.title = request.POST[key].strip()
                    item.save()

            # Add new reading items
            for title in request.POST.getlist("new_reading_item"):
                if title.strip():
                    StudentChecklistItem.objects.create(
                        lesson=lesson,
                        title=title.strip(),
                        item_type="READING"
                    )

            # Update existing assignment items
            for item in lesson.checklist_items.filter(item_type="ASSIGNMENT"):
                key = f"assignment_item_{item.id}"
                if key in request.POST:
                    item.title = request.POST[key].strip()
                    item.save()

            # Add new assignment items
            for title in request.POST.getlist("new_assignment_item"):
                if title.strip():
                    StudentChecklistItem.objects.create(
                        lesson=lesson,
                        title=title.strip(),
                        item_type="ASSIGNMENT"
                    )

            messages.success(request, f"Lesson '{lesson.title}' updated successfully!")
            return redirect("lesson_detail_edit", pk=lesson.pk)
        else:
            messages.error(request, f"Please fix the errors below.")
            print("Form errors:", form.errors)
            print("Formset errors:", formset.errors)
    else:
        form = LessonDetailForm(instance=lesson, course=course, request=request)
        formset = LessonTaskFormSet(instance=lesson)

    reading_items = lesson.checklist_items.filter(item_type="READING")
    assignment_items = lesson.checklist_items.filter(item_type="ASSIGNMENT")

    return render(request, "lesson_detail_edit.html", {
        "lesson": lesson,
        "lesson_form": form,
        "formset": formset,
        "course": course,
        "available_classrooms": available_classrooms,
        "total_points": total_points,
        "remaining_points": remaining_points,
        "reading_items": reading_items,
        "assignment_items": assignment_items,
    })

@role_required("INSTRUCTOR")
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

@role_required("INSTRUCTOR")
def delete_lesson(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk, designer=request.user)
    course_pk = lesson.course.pk
    lesson.delete()
    messages.success(request, "Lesson deleted successfully!")
    return redirect("course_detail", pk=course_pk)

@role_required("STUDENT")
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

@role_required("STUDENT")
def unenrol_lesson(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk)
    student = request.user
    
    enrolment = Enrolment.objects.filter(student=student, lesson=lesson, completed=False).first()
    if enrolment:
        enrolment.delete()  
    return redirect("student_course_details", pk=lesson.course.pk)

@role_required("INSTRUCTOR")
def instructor_classroom(request):
    instructor = request.user
    classrooms = (
        Classroom.objects
        .select_related("course_id")
        .prefetch_related("lessons")
        .filter(course_id__instructor=instructor)  
        .distinct()
    )

    return render(request, "instructor_classroom.html", {
        "classrooms": classrooms,
    })

@role_required("INSTRUCTOR")
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

@role_required("INSTRUCTOR")
def create_classroom(request, pk=None):
    preselected_course = get_object_or_404(Course, pk=pk) if pk else None

    if request.method == "POST":
        form = ClassroomForm(request.POST, request=request, preselected_course=preselected_course)
        if form.is_valid():
            classroom = form.save(commit=False)
            if preselected_course:
                classroom.course_id = preselected_course
            classroom.save()
            messages.success(request, "Classroom created successfully.")
            # after global creation, return to instructor_classroom
            return redirect("instructor_classroom")
    else:
        form = ClassroomForm(request=request, preselected_course=preselected_course)

    return render(request, "create_classroom.html", {
        "form": form,
        "course": preselected_course,
    })

@role_required("INSTRUCTOR")
def delete_classroom(request, pk):
    classroom = get_object_or_404(Classroom, pk=pk)
    course_pk = classroom.course_id.pk   
    
    if request.method == "POST":  
        classroom.delete()
        messages.success(request, "Classroom deleted successfully!")
        return redirect("course_detail", pk=course_pk)

from django.db.models import Prefetch
@login_required
def student_profile(request):
    profile = get_object_or_404(StudentProfile, user=request.user)
    courses = Course.objects.filter(students=request.user)

    # Prefetch only published lessons for each course
    courses = courses.prefetch_related(
        Prefetch("lessons", queryset=Lesson.objects.filter(status="PUBLISHED"))
    )

    enrolments = Enrolment.objects.filter(student=request.user).select_related("lesson")
    enrolments_map = {e.lesson.id: e for e in enrolments}

    # Attach status to each published lesson
    for course in courses:
        for lesson in course.lessons.all():  # only published lessons
            lesson.enrolment = enrolments_map.get(lesson.id)

            # Total checklist items for this lesson
            total_items = StudentChecklistItem.objects.filter(lesson=lesson).count()

            # Completed checklist items by student
            completed_items = StudentChecklistProgress.objects.filter(
                student=request.user,
                item__lesson=lesson,
                completed=True
            ).count()

            # Decide lesson status
            if total_items > 0 and completed_items == total_items:
                lesson.status = "Completed"
            elif completed_items > 0:
                lesson.status = "In Progress"
            else:
                if lesson.enrolment:
                    lesson.status = "Not Started"
                else:
                    lesson.status = "Not Enrolled"

    # Calculate total credit earned
    total_credit = sum(e.credit_earned for e in enrolments)

    return render(request, "student_profile.html", {
        "profile": profile,
        "courses": courses,
        "total_credit": total_credit,
    })


@role_required("STUDENT")
def student_report_course(request):
    student = request.user
    enrolled = student.courses_enroling.all()

    return render(request, "student_report_course.html", {"courses":enrolled})

@role_required("STUDENT")
def student_report_course_details(request, pk):
    course = get_object_or_404(Course, pk=pk)
    student = request.user

    # Only active lessons
    active_lessons = course.lessons.filter(status="PUBLISHED")

    # Checklist items by type
    reading_items = StudentChecklistItem.objects.filter(lesson__in=active_lessons, item_type="READING")
    assignment_items = StudentChecklistItem.objects.filter(lesson__in=active_lessons, item_type="ASSIGNMENT")

    # Student progress for checklist
    reading_done = StudentChecklistProgress.objects.filter(student=student, item__in=reading_items, completed=True).count()
    assignment_done = StudentChecklistProgress.objects.filter(student=student, item__in=assignment_items, completed=True).count()

    # Totals
    total_readings = reading_items.count()
    total_assignments = assignment_items.count()

    reading_left = total_readings - reading_done
    assignment_left = total_assignments - assignment_done

    reading_percent = (reading_done / total_readings * 100) if total_readings else 0
    assignment_percent = (assignment_done / total_assignments * 100) if total_assignments else 0

    total_item = total_readings + total_assignments
    total_done = reading_done + assignment_done
    total_percentage = (total_done / total_item * 100) if total_item else 0

    context = {
        "course": course,
        "reading_percent": round(reading_percent, 1),
        "assignment_percent": round(assignment_percent, 1),
        "total_readings": total_readings,
        "total_assignments": total_assignments,
        "reading_done": reading_done,
        "assignment_done": assignment_done,
        "reading_left": reading_left,
        "assignment_left": assignment_left,
        "total_item": total_readings + total_assignments,
        "total_done": total_done,
        "total_percent": total_percentage,
    }
    return render(request, "student_report_course_details.html", context)

@role_required("STUDENT")
def student_change_password(request):
    if request.method == "POST":
        form = StudentPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            new_password = form.cleaned_data["new_password"]
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)  
            messages.success(request, "Your password has been changed successfully.")
            return redirect("student_profile")  
        else:
            messages.error(request, "Unable to change password. Please correct the errors below.")
    else:
        form = StudentPasswordChangeForm(request.user)
    return render(request, "student_change_password.html", {"form": form})