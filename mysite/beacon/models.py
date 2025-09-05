from django.db import models
from django.contrib.auth.models import User

# Create your models here.

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
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="courses_teaching")
    students = models.ManyToManyField(User, related_name="courses_enroling", blank=True)

    def __str__(self):
        return f"{self.course_id} - {self.title}"
    