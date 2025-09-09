from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.apps import apps

@receiver(post_migrate)
def create_default_groups(sender, **kwargs):
    if sender.name == "beacon":
        instructor_group, _ = Group.objects.get_or_create(name = "Instructors")
        students_group, _ = Groups.objects.get_or_create(name = "Students")

        course_model = apps.get_model("beacon", "Course")
        perms = Permission.objects.filter(content_type__app_label = "beacon", content_type__model = "course")
        instructor_group.permissions.set(perms)

        