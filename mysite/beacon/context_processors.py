from .models import StudentProfile, InstructorProfile

def user_dark_mode(request):
    dark_mode = request.session.get("dark_mode", False)
    if request.user.is_authenticated:
        if request.user.role.upper() == "STUDENT":
            dark_mode = getattr(request.user.studentprofile, "dark_mode", False)
        elif request.user.role.upper() == "INSTRUCTOR":
            dark_mode = getattr(request.user.instructorprofile, "dark_mode", False)
    return {"dark_mode": dark_mode}
