from django.utils import timezone
from .models import Course, Enrolment, LessonClassroomAllocation, StudentChecklistItem, StudentChecklistProgress

def get_completed_courses(user, auto_unenroll=True):
    completed_courses = []

    # Get all courses that actually have lessons
    courses = Course.objects.filter(lessons__isnull=False).distinct()
    for course in courses:
        lessons = course.lessons.all()

        enrolments = Enrolment.objects.filter(student=user, lesson__in=lessons)
        if enrolments.count() != lessons.count():
            continue
        if enrolments.filter(completed=False).exists():
            continue

        checklist_items = StudentChecklistItem.objects.filter(lesson__in=lessons)
        checklist_progress = StudentChecklistProgress.objects.filter(
            student=user,
            item__in=checklist_items
        )
        if checklist_items.count() != checklist_progress.count():
            continue
        if checklist_progress.filter(completed=False).exists():
            continue

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