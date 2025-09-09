from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver
from django.apps import apps
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(post_migrate)
def create_default_groups(sender, **kwargs):
    if sender.name == "beacon":
        instructors_group, _ = Group.objects.get_or_create(name = "Instructors")
        students_group, _ = Group.objects.get_or_create(name = "Students")

        course_model = apps.get_model("beacon", "Course")
        ins_perms = Permission.objects.filter(content_type__app_label = "beacon", content_type__model = "course")
        stu_perms = Permission.objects.filter(content_type__app_label = "beacon", content_type__model = "course", codename__startswith = "view_")
        instructors_group.permissions.set(ins_perms)
        students_group.permissions.set(stu_perms)

@receiver(post_save, sender=User)
def add_user_to_group(sender, instance, created, **kwargs):
    if not created:
        instance.groups.clear()
        if instance.role == User.Role.INSTRUCTOR:
            group, _ = Group.objects.get_or_create(name="Instructors")
            instance.groups.add(group)
        elif instance.role == User.Role.STUDENT:
            group, _ = Group.objects.get_or_create(name="Students")
            instance.groups.add(group)
    
    if instance.role == User.Role.INSTRUCTOR:
        group, _ = Group.objects.get_or_create(name="Instructors")
        instance.groups.add(group)
    elif instance.role == User.Role.STUDENT:
        group, _ = Group.objects.get_or_create(name="Students")
        instance.groups.add(group)