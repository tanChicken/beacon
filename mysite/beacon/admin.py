from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import TodoItem, Profile, Course

# Register TodoItem
admin.site.register(TodoItem)

# Register Profile and show role inline with User
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Profile"

class CustomUserAdmin(DjangoUserAdmin):
    inlines = (ProfileInline,)
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "get_role")

    def get_role(self, obj):
        return obj.profile.role if hasattr(obj, "profile") else "-"
    get_role.short_description = "Role"

# Unregister the default User and re-register with Profile inline
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Register Course
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("course_id", "title", "status", "instructor")
    list_filter = ("status",)
    search_fields = ("course_id", "title")
    filter_horizontal = ("students",)