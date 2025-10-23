from django.utils import timezone
from django.db.models import Sum
from .models import Course, Enrolment, Lesson, LessonClassroomAllocation, StudentChecklistItem, StudentChecklistProgress

def get_completed_courses(user, auto_unenroll=True):
    completed_courses = []

    # Get all courses that actually have lessons
    courses = Course.objects.filter(lessons__isnull=False).distinct()
    for course in courses:
        lessons = course.lessons.all()

        # Get enrolments for this student and course
        enrolments = Enrolment.objects.filter(student=user, lesson__in=lessons)

        # Skip if not enrolled in any lessons
        if not enrolments.exists():
            continue

        # --- Step 1: Sum credit points of completed lessons only ---
        completed_lessons = enrolments.filter(completed=True).values_list("lesson", flat=True)
        total_completed_credit = (
            Lesson.objects.filter(pk__in=completed_lessons)
            .aggregate(total=Sum("credit_point"))
            .get("total") or 0
        )

        # --- Step 2: Check if total credit ≥ 30 ---
        if total_completed_credit < 30:
            continue  # Not enough credit to complete the course

        # --- Step 3: Optional checklist validation (optional, can keep or remove) ---
        checklist_items = StudentChecklistItem.objects.filter(lesson__in=lessons)
        checklist_progress = StudentChecklistProgress.objects.filter(
            student=user,
            item__in=checklist_items
        )

        # If checklist exists but not all completed, skip
        if checklist_items.exists():
            if checklist_progress.filter(completed=False).exists() or \
               checklist_progress.count() < checklist_items.count():
                continue

        # --- Step 4: Mark course as completed ---
        completed_courses.append(course.pk)

        if auto_unenroll and user.courses_enroling.filter(pk=course.pk).exists():
            user.courses_enroling.remove(course)

    return Course.objects.filter(pk__in=completed_courses)

def expire_old_allocations():
    """Remove expired allocations and their related enrolments/progress."""
    today = timezone.now().date()
    expired_allocs = LessonClassroomAllocation.objects.filter(expiry_date__lt=today)
    expired_lessons = []

    for alloc in expired_allocs:
        lesson = alloc.lesson
        expired_lessons.append(str(lesson))  # store name/title for message

        # Delete related enrolments for this lesson
        Enrolment.objects.filter(lesson=lesson).delete()

        # Delete checklist progress linked to that lesson
        StudentChecklistProgress.objects.filter(item__lesson=lesson).delete()

        # Finally remove the allocation itself
        alloc.delete()
    
    return expired_lessons