from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


# ------------------------
# Todo List Example
# ------------------------
class TodoItem(models.Model):
    title = models.CharField(max_length=200)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return self.title


# ------------------------
# Course Model
# ------------------------
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
    instructor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="courses_teaching"
    )
    students = models.ManyToManyField(
        User,
        related_name="courses_enroling",
        blank=True
    )

    def __str__(self):
        return f"{self.course_id} - {self.title}"


# ------------------------
# User Profile for Roles
# ------------------------
class Profile(models.Model):
    ROLE_CHOICES = [
        ("student", "Student"),
        ("instructor", "Instructor"),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="student")

    def __str__(self):
        return f"{self.user.username} ({self.role})"


# ------------------------
# Automatically create Profile when User is created
# ------------------------
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()