from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db.models.signals import post_save 
from django.dispatch import receiver
from django.utils import timezone

# Create your models here.

# demo
class TodoItem(models.Model):
    title = models.CharField(max_length=200)
    completed = models.BooleanField(default=False)

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
    
class Classroom(models.Model):
    DURATION_CHOICES = [
        (2, "2 weeks"),
        (3, "3 weeks"),
        (4, "4 weeks"),
    ]
    classroom_id = models.CharField(max_length=20)
    course_id = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="classrooms")
    duration_weeks = models.PositiveIntegerField(choices=DURATION_CHOICES)
    supervisor = models.CharField(max_length=100)

    # Location attributes
    building = models.CharField(max_length=100, blank=True, null=True)
    room = models.CharField(max_length=50, blank=True, null=True)
    online_link = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"Classroom {self.id} for {self.course.course_code} ({self.duration_weeks} weeks)"

    def location_display(self):
        if self.online_link:
            return f"Online class link: {self.online_link}"
        elif self.building and self.room:
            return f"{self.building}, Room {self.room}"
        return "TBA"

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
    
@receiver(post_save, sender=Student)
def create_student_profile(sender, instance, created, **kwargs):
    if created and instance.role == "STUDENT":
        StudentProfile.objects.create(user=instance)

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
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="instructorprofile")
    bio = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Instructor Profile: {self.user.email}"

@receiver(post_save, sender=Instructor)
def create_instructor_profile(sender, instance, created, **kwargs):
    if created and instance.role == "INSTRUCTOR":
        InstructorProfile.objects.create(user=instance)
    
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profiles(sender, instance, created, **kwargs):
    if not created:
        return
    role = getattr(instance, "role", None)
    if role in (getattr(User.Role, "STUDENT", "STUDENT"), "STUDENT"):
        StudentProfile.objects.get_or_create(user=instance)
    if role in (getattr(User.Role, "INSTRUCTOR", "INSTRUCTOR"), "INSTRUCTOR"):
        InstructorProfile.objects.get_or_create(user=instance)  

class Classroom(models.Model):
    DURATION_CHOICES = [
        (2, "2 weeks"),
        (3, "3 weeks"),
        (4, "4 weeks"),
    ]
    classroom_id = models.CharField(max_length=20)
    course_id = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="classrooms")
    duration_weeks = models.PositiveIntegerField(choices=DURATION_CHOICES)
    supervisor = models.CharField(max_length=100)

    # Location attributes
    building = models.CharField(max_length=100, blank=True, null=True)
    room = models.CharField(max_length=50, blank=True, null=True)
    online_link = models.URLField(blank=True, null=True)

    def _str_(self):
        return f"Classroom {self.id} for {self.course.course_code} ({self.duration_weeks} weeks)"

    def location_display(self):
        if self.online_link:
            return f"Online class link: {self.online_link}"
        elif self.building and self.room:
            return f"{self.building}, Room {self.room}"
        return "TBA"

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons", null=True, blank=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, blank=True, related_name="lessons")
    lesson_id = models.CharField(max_length=10, unique=False, editable=False)  
    title = models.CharField(max_length=200)
    description = models.TextField()
    objective = models.TextField(blank=True, null=True)
    designer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="lessons"
    )
    enrolled_students = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="enrolled_lessons", blank=True)
    effort_per_week = models.PositiveIntegerField(default=0)
    credit_point = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assignment = models.TextField(blank=True, null=True)
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("PUBLISHED", "Published"),
        ("ARCHIVED", "Archived"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,default="DRAFT")

    def save(self, *args, **kwargs):
        if not self.lesson_id:
            count = Lesson.objects.filter(course=self.course).count() + 1
            self.lesson_id = f"L{count:03d}"   
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.lesson_id} - {self.title}"

class StudentReadingListItem(models.Model):
    lesson = models.ForeignKey(Lesson, related_name="reading_items", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.lesson.title} - {self.title}"

class StudentReadingListProgress(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    item = models.ForeignKey(StudentReadingListItem, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ("student", "item")

    def __str__(self):
        return f"{self.student.email} - {self.item.title}: {'Done' if self.completed else 'Not Done'}"
    