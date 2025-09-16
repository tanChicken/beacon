from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
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
    credit_points = 30
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
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="instructorprofile")
    bio = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Instructor Profile: {self.user.username}"

@receiver(post_save, sender=Instructor)
def create_user_profile(sender, instance, created, **kwargs):
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

class Lesson(models.Model):
    lesson_id = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    objective = models.TextField(blank=True, null=True)
    reading_list = models.TextField(blank=True, null=True)
    designer = models.ForeignKey(
        Instructor, on_delete=models.SET_NULL, null=True, related_name="lessons"
    )
    effort_per_week = models.PositiveIntegerField(default=0)
    credit_point = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.lesson_id} - {self.title}"
