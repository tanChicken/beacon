from django.db import models
from django.conf import settings
from django.contrib.auth.models import User, AbstractUser, BaseUserManager

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
        TEACHER = "TEACHER", "Teacher"

    base_role = Role.ADMIN

    role = models.CharField(max_length=50, choices=Role.choices)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.role = self.base_role
            return super().save(*args, **kwargs)

class StudentManager(BaseUserManager):
    def get_queryset(self, *args, **kwargs):
        results = super().get_queryset(*args, **kwargs)
        return results.filter(role=User.Role.STUDENT)


class Student(User):
    base_role =  User.Role.STUDENT

    student = StudentManager

    class Meta:
        proxy = True

    def welcome(self):
        return "Only for students"       

class TeacherManager(BaseUserManager):
    def get_queryset(self, *args, **kwargs):
        results = super().get_queryset(*args, **kwargs)
        return results.filter(role=User.Role.TEACHER)


class Teacher(User):
    base_role =  User.Role.TEACHER

    teacher = TeacherManager

    class Meta:
        proxy = True

    def welcome(self):
        return "Only for teachers"       
    


    