from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class TodoItem(models.Model):
    title = models.CharField(max_length=200)
    completed = models.BooleanField(default=False)

# class User(AbstractUser):
#     class Role(models.TextChoices):
#         STUDENT = "STUDENT", 'Student'
#         INSTRUCTOR = "INSTRUCTOR", 'Instructor'

#     role = models.CharField(
#         max_length=50,
#         choices=Role.choices,
#         default=Role.STUDENT,      
#     )  
