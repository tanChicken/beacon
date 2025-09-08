from django.contrib import admin
from .models import TodoItem, User, Course
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin


# Register your models here.
admin.site.register(TodoItem)
@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    # show custom field in the User admin
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Role", {"fields": ("role",)}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "password1", "password2", "role"),
        }),
    )
    list_display = ("username", "email", "first_name", "last_name", "role", "is_staff")
    list_filter = DjangoUserAdmin.list_filter + ("role",)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("course_id", "title", "status", "instructor")
    list_filter = ("status",)
    search_fields = ("course_id", "title")
    filter_horizontal = ("students",)  # nicer M2M widget

# @admin.register(TodoItem)
# class TodoItemAdmin(admin.ModelAdmin):
#     list_display = ("title", "completed")