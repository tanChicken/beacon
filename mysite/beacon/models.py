from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db.models.signals import post_save 
from django.dispatch import receiver

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
            ("draft", "Draft"),
            ("active", "Active"),
            ("archived", "Archived"),
        ],
        default="draft"
    )
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="courses_teaching")
    students = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="courses_enroling", blank=True)

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
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    instructor_id = models.IntegerField(null=True, blank=True)


@receiver(post_save, sender=Instructor)
def create_user_profile(sender, instance, created, **kwargs):
    if created and instance.role == "INSTRUCTOR":
        InstructorProfile.objects.create(user=instance)
    


    