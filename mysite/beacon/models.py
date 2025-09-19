from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save 
from django.dispatch import receiver
from django.utils import timezone



# Demo
class TodoItem(models.Model):
    title = models.CharField(max_length=200)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return self.title


# ------------------------
# User Profile for Roles
# ------------------------
class Profile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('student', 'Student'),
        ('instructor', 'Instructor'),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"


@receiver(post_save, sender='beacon.User')
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender='beacon.User')
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


# ------------------------
# Course Model
# ------------------------
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
    
class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        STUDENT = "STUDENT", "Student"
        INSTRUCTOR = "INSTRUCTOR", "Instructor"

    base_role = Role.ADMIN

    role = models.CharField(max_length=50, choices=Role.choices)

    def save(self, *args, **kwargs):
        if not self.pk and not self.role:
            self.role = self.base_role
        return super().save(*args, **kwargs)

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
def create_user_profile(sender, instance, created, **kwargs):
    if created and instance.role == "STUDENT":
        StudentProfile.objects.create(user=instance)

class StudentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    student_id = models.IntegerField(null=True, blank=True)
    title = models.CharField(
        max_length=10,
        choices=[("Mr", "Mr"), ("Ms", "Ms"), ("Mrs", "Mrs"), ("Dr", "Dr")],
        default="Mr"
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
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="instructorprofile")
    bio = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Instructor Profile: {self.user.username}"

@receiver(post_save, sender=Instructor)
def create_user_profile(sender, instance, created, **kwargs):
    if created and instance.role == "INSTRUCTOR":
        InstructorProfile.objects.create(user=instance)
    
@receiver(post_save, sender='beacon.User')
def ensure_profiles(sender, instance, created, **kwargs):
    if not created:
        return
    role = getattr(instance, "role", None)
    if role in (getattr(User.Role, "STUDENT", "STUDENT"), "STUDENT"):
        StudentProfile.objects.get_or_create(user=instance)
    if role in (getattr(User.Role, "INSTRUCTOR", "INSTRUCTOR"), "INSTRUCTOR"):
        InstructorProfile.objects.get_or_create(user=instance)  

import uuid
class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons", null=True, blank=True)
    lesson_id = models.CharField(max_length=10, unique=False, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    objective = models.TextField(blank=True, null=True)
    designer = models.ForeignKey(
        Instructor, on_delete=models.SET_NULL, null=True, related_name="lessons"
    )
    enrolled_students = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="enrolled_lessons", blank=True)
    effort_per_week = models.PositiveIntegerField(default=0)
    credit_point = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
        return f"{self.lesson.title} – {self.title}"

class StudentReadingListProgress(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    item = models.ForeignKey(StudentReadingListItem, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ("student", "item")

    def __str__(self):
        return f"{self.student.username} – {self.item.title}: {'Done' if self.completed else 'Not Done'}"