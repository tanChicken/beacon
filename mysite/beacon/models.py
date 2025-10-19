from datetime import timedelta
from django.db import models, transaction
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db.models.signals import post_save 
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import Max

# Demo
class TodoItem(models.Model):
    title = models.CharField(max_length=200)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return self.title

class Course(models.Model):
    course_id = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("inactive", "Inactive"),
        ],
        default="active"
    )
    credit_points = models.IntegerField(default=30, editable=False)
    created_at = models.DateTimeField(default=timezone.now)  # when course is first created
    updated_at = models.DateTimeField(auto_now=True)      # automatically updated on save
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="courses_teaching")
    students = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="courses_enroling", blank=True)
    #lessons = 
    #classroom_count = 

    def __str__(self):
        return f"{self.course_id} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.course_id:
            latest = Course.objects.aggregate(Max("course_id"))["course_id__max"]
            if latest:
                num = int(latest[1:])
                new_num = num + 1
            else:
                new_num = 1
            self.course_id = f"C{new_num:03d}"
        super().save(*args, **kwargs)
    
class Classroom(models.Model):
    DURATION_CHOICES = [
        (2, "2 weeks"),
        (3, "3 weeks"),
        (4, "4 weeks"),
    ]
    classroom_id = models.CharField(max_length=20, unique=True)
    course_id = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="classrooms")
    duration_weeks = models.PositiveIntegerField(choices=DURATION_CHOICES)
    supervisor = models.CharField(max_length=100)

    # Location attributes
    building = models.CharField(max_length=100, blank=True, null=True)
    room = models.CharField(max_length=50, blank=True, null=True)
    online_link = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"Classroom {self.classroom_id} for {self.course_id.course_id} ({self.duration_weeks} weeks)"

    def location_display(self):
        if self.online_link:
            return f"Online class link: {self.online_link}"
        elif self.building and self.room:
            return f"{self.building}, Room {self.room}"
        return "TBA"
    
    def save(self, *args, **kwargs):
        if not self.classroom_id and self.course_id:
            existing_ids = (
                Classroom.objects.filter(course_id=self.course_id)
                .values_list("classroom_id", flat=True)
            )
            used_numbers = [
                int(cid.split("-CL")[-1])
                for cid in existing_ids if cid and "-CL" in cid
            ]
            n = 1
            while n in used_numbers:
                n += 1
            self.classroom_id = f"{self.course_id.course_id}-CL{n:02d}"
        super().save(*args, **kwargs)

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password, role, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        if not password:
            raise ValueError("Password is required")
        if not role:
            raise ValueError("Role is required")
        
        email = self.normalize_email(email)
        user = self.model(email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, role="ADMIN", **extra_fields)
   
class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        STUDENT = "STUDENT", "Student"
        INSTRUCTOR = "INSTRUCTOR", "Instructor"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=50, choices=Role.choices)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_semester_active = models.BooleanField(default=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()    

class StudentManager(models.Manager):
    def get_queryset(self, *args, **kwargs):
        results = super().get_queryset(*args, **kwargs)
        return results.filter(role=User.Role.STUDENT)


class Student(User):
    base_role =  User.Role.STUDENT

    student = StudentManager()

    class Meta:
        proxy = True

    def welcome(self):
        return "Only for students"       

class StudentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)

    title = models.CharField(
        max_length=10,
        choices=[("Mr", "Mr"), ("Ms", "Ms"), ("Mrs", "Mrs"), ("Dr", "Dr")],
        default="Mr",
        blank=True,
        null=True
    )
    dark_mode = models.BooleanField(default=False)
    graduated = models.BooleanField(default=False)
    graduation_date = models.DateField(blank=True, null=True)

    font_size = models.CharField(
        max_length=10,
        choices=[
            ("small", "Small"),
            ("medium", "Medium"),
            ("large", "Large"),
        ],
        default="medium",
    )

    def __str__(self):
        return f"{self.title or ''} {self.first_name or ''} {self.last_name or ''}".strip()
    
    
@receiver(post_save, sender=Student)
def create_student_profile(sender, instance, created, **kwargs):
    if created and instance.role == "STUDENT":
        StudentProfile.objects.create(user=instance)

class InstructorManager(models.Manager):
    def get_queryset(self, *args, **kwargs):
        results = super().get_queryset(*args, **kwargs)
        return results.filter(role=User.Role.INSTRUCTOR)

class Instructor(User):
    base_role =  User.Role.INSTRUCTOR

    instructor = InstructorManager()

    class Meta:
        proxy = True

    def welcome(self):
        return "Only for instructors"       
    
class InstructorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="instructorprofile")
    bio = models.TextField(blank=True, null=True)
    dark_mode = models.BooleanField(default=False)
    font_size = models.CharField(
        max_length=10,
        choices=[
            ("small", "Small"),
            ("medium", "Medium"),
            ("large", "Large"),
        ],
        default="medium",
    )

    def __str__(self):
        return f"Instructor Profile: {self.user.email}"

@receiver(post_save, sender=Instructor)
def create_instructor_profile(sender, instance, created, **kwargs):
    if created and instance.role == "INSTRUCTOR":
        InstructorProfile.objects.create(user=instance)
    
@receiver(post_save, sender=User)
def ensure_profiles(sender, instance, created, **kwargs):
    if created:
        if instance.role == User.Role.STUDENT:
            StudentProfile.objects.get_or_create(user=instance)
        elif instance.role == User.Role.INSTRUCTOR:
            InstructorProfile.objects.get_or_create(user=instance)

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons", null=True, blank=True)
    lesson_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    objective = models.TextField(blank=True, null=True)
    designer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="lessons"
    )
    effort_per_week = models.PositiveIntegerField(default=0)
    credit_point = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assignment = models.TextField(blank=True, null=True)
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("PUBLISHED", "Published"),
        ("ARCHIVED", "Archived"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,default="DRAFT")
    prerequisites = models.ManyToManyField("self", symmetrical=False, blank=True, related_name="unlocking_lessons")

    def __str__(self):
        return f"{self.lesson_id} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.lesson_id and self.course:
            existing_ids = Lesson.objects.filter(course=self.course).values_list("lesson_id", flat=True)
            used_numbers = [
                int(lid.split("-")[-1])
                for lid in existing_ids
                if lid and "-" in lid and lid.split("-")[-1].isdigit()
            ]

            n = 1
            while n in used_numbers:
                n += 1

            self.lesson_id = f"{self.course.course_id}-{n}"

        if self.effort_per_week < 1:
            self.effort_per_week = 1

        super().save(*args, **kwargs)
    
class LessonTask(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="tasks")
    description = models.CharField(max_length=255)
    estimated_time = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.lesson.title} - {self.description}"


class StudentChecklistItem(models.Model):
    CHECKLIST_TYPE_CHOICES = [
        ("READING", "Reading"),
        ("ASSIGNMENT", "Assignment"),
        ("OTHER", "Other"),
    ]

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="checklist_items")
    title = models.CharField(max_length=255)
    item_type = models.CharField(max_length=20, choices=CHECKLIST_TYPE_CHOICES, default="OTHER")
    deadline = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} ({self.item_type})"

class StudentChecklistProgress(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    item = models.ForeignKey(StudentChecklistItem, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ("student", "item")

    def __str__(self):
        return f"{self.student.email} - {self.item.title}: {'Done' if self.completed else 'Not Done'}"
    
class LessonClassroomAllocation(models.Model):
    PERIOD_CHOICES = [
        (2, "2 Weeks"),
        (3, "3 Weeks"),
        (4, "4 Weeks"),
    ]

    lesson = models.ForeignKey("Lesson", on_delete=models.CASCADE, related_name="allocations")
    classroom = models.ForeignKey("Classroom", on_delete=models.CASCADE, related_name="allocations")
    period_weeks = models.IntegerField(choices=PERIOD_CHOICES)
    start_date = models.DateField(default=timezone.now)
    expiry_date = models.DateField(blank=True, null=True)
    schedule = models.CharField(max_length=100, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.period_weeks:
            try:
                self.period_weeks = int(self.period_weeks)
            except (TypeError, ValueError):
                pass  # leave it unchanged if it's invalid

        if not self.expiry_date and self.start_date and self.period_weeks:
            self.expiry_date = self.start_date + timedelta(weeks=int(self.period_weeks))

        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now().date() > self.expiry_date

    def __str__(self):
        return f"{self.lesson.title} → {self.classroom.classroom_id} ({self.period_weeks} weeks)"

class Enrolment(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrolments"
    )
    lesson = models.ForeignKey(
        "Lesson",
        on_delete=models.CASCADE,
        related_name="enrolments"
    )
    completed = models.BooleanField(default=False)  
    enrolled_at = models.DateTimeField(auto_now_add=True)
    credit_earned = models.IntegerField(default=0)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="enrolments", null=True, blank=True)  # NEW
    allocation = models.ForeignKey(LessonClassroomAllocation, on_delete=models.SET_NULL, null=True, blank=True)  # NEW

    class Meta:
        unique_together = ("student", "lesson")

    def mark_completed(self):
        self.completed = True
        self.completed_at = timezone.now()
        self.save()

    def __str__(self):
        status = "Completed" if self.completed else "In Progress"
        return f"{self.student.email} enrolled in {self.lesson.title} ({status})"
    
    @staticmethod
    def unenrol_student_from_course(student, course):
        with transaction.atomic():
            lessons = Lesson.objects.filter(course=course)
            Enrolment.objects.filter(student=student, lesson__in = lessons).delete()
            checklist_items = StudentChecklistItem.objects.filter(lesson__in=lessons)
            StudentChecklistProgress.objects.filter(student=student, item__in=checklist_items).delete()