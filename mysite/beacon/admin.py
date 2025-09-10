from django.contrib import admin
from .models import TodoItem, Course, StudentProfile, InstructorProfile
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin


# Register your models here.
User = get_user_model()


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    extra = 0
    fk_name = "user"          # must match your OneToOneField name in StudentProfile


class InstructorProfileInline(admin.StackedInline):
    model = InstructorProfile
    can_delete = False
    extra = 0
    fk_name = "user"

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    # CHANGE view (edit existing user)
    fieldsets = (
        *DjangoUserAdmin.fieldsets,
        ("Role", {"fields": ("role",)}),
    )
    # ADD view (create new user) — replace, don’t append
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "password1", "password2", "role"),
        }),
    )
    list_display = ("username", "email", "first_name", "last_name", "role", "is_staff")
    list_filter = (*DjangoUserAdmin.list_filter, "role")
    search_fields = ("username", "email", "first_name", "last_name")

    # inlines = [StudentProfileInline, InstructorProfileInline]

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "title")           # add more fields as you have them
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name")


@admin.register(InstructorProfile)
class InstructorProfileAdmin(admin.ModelAdmin):
    list_display = ("user",)
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name")

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("course_id", "title", "status", "instructor")
    list_filter = ("status",)
    search_fields = ("course_id", "title")
    filter_horizontal = ("students",)  # nicer M2M widget

# @admin.register(TodoItem)
# class TodoItemAdmin(admin.ModelAdmin):
#     list_display = ("title", "completed")