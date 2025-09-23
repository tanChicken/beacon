from django import forms
from .models import Course, StudentReadingListItem, User, StudentProfile, Instructor, Lesson, Classroom, LessonTask
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from django.db import models

class StudentSignupForm(forms.ModelForm):
    title_choices = [
        ('Mr', 'Mr'),
        ('Ms', 'Ms'),
    ]
    title = forms.ChoiceField(choices=title_choices)
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    confirm_password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    first_name = forms.CharField(max_length=30, label="First Name")
    last_name = forms.CharField(max_length=30, label="Last Name")

    class Meta:
        model = User
        fields = ["email", "role"]

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match.")
        
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()

            StudentProfile.objects.create(
                user=user,
                first_name = self.cleaned_data["first_name"],
                last_name = self.cleaned_data["last_name"],
                student_id = "TEMP"
            )
        return user

class StudentLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

class InstructorLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

class CourseForm(forms.ModelForm):
    instructor = forms.ModelChoiceField(
        queryset=Instructor.instructor.all(),
        required=True,
        label="Course Director",
        empty_label="Select Instructor",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = Course
        fields = ["course_id", "title", "status", "instructor"]
        widgets = {
            "course_id": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. CRS-001"}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Course Title"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ["title"]

LessonFormSet = inlineformset_factory(
    Course, Lesson, form=LessonForm, extra=1, can_delete=False
)

class LessonDetailForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['status', 'lesson_id', 'title', 'lesson_point', 'description', 'objective', 'assignment', 'prerequisites', 'effort_per_week']
        widgets = {
            "lesson_id": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. LSN-001"}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Lesson Title"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Write a short description"}),
            "objective": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Learning objectives"}),
            "effort_per_week": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Hours per week"}),
            "assignment": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Assignment details"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "lesson_point": forms.NumberInput(attrs={"class": "form-control", "min": 0, "max": 30}),
            "prerequisites": forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"})
        }

    def __init__(self, *args, **kwargs):
        self.course = kwargs.pop("course", None)
        self.instance = kwargs.get("instance", None)
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        if self.course:
            self.fields["prerequisites"].queryset = Lesson.objects.filter(course=self.course).exclude(pk=self.instance.pk if self.instance else None)

        fld = self.fields.get("classroom")
        if fld:
            fld.required = False
            # Nice placeholder option
            fld.empty_label = "-- No classroom assigned --"

            qs = Classroom.objects.all()

            # Typically: only classrooms belonging to this course
            if self.course:
                # qs = qs.filter(course=self.course)
                qs = qs.filter(course_id=self.course)


            # Optional: further restrict to classrooms owned by the logged-in instructor
            if request and getattr(request, "user", None) and request.user.is_authenticated:
                # Only if your Classroom ties to Course.instructor
                # qs = qs.filter(course__instructor=request.user)
                qs = qs.filter(course_id__instructor=request.user)


            fld.queryset = qs.order_by("classroom_id")

    def clean_lesson_id(self):
        lesson_id = self.cleaned_data.get("lesson_id")
        if lesson_id and Lesson.objects.filter(lesson_id=lesson_id).exists():
            if self.instance and self.instance.lesson_id == lesson_id:
                return lesson_id
            raise forms.ValidationError("This lesson ID already exists. Please choose a different one.")
        return lesson_id
    
    def clean_lesson_point(self):
        lesson_point = self.cleaned_data.get("lesson_point", 0)

        if self.course:
            total_existing = (
                Lesson.objects.filter(course=self.course)
                .exclude(pk=self.instance.pk if self.instance else None)
                .aggregate(total=models.Sum("lesson_point"))["total"] or 0
            )
        else:
            total_existing = 0

        total_after = total_existing + lesson_point
        if total_after > 30:
            raise forms.ValidationError(
                f"Total credit points for this course cannot exceed 30 (currently {total_existing})."
            )
        return lesson_point

class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ["title", "description"]


class LessonTaskForm(forms.ModelForm):
    class Meta:
        model = LessonTask
        fields = ["description", "estimated_time"]

LessonTaskFormSet = inlineformset_factory(
    Lesson, LessonTask,
    form=LessonTaskForm,
    extra=1,
    can_delete=True
)
        
class ReadingItemForm(forms.ModelForm):
    class Meta:
        model = StudentReadingListItem
        fields = ["title"]

DURATION_CHOICES = [(2, "2 weeks"), (3, "3 weeks"), (4, "4 weeks")]
class ClassroomForm(forms.ModelForm):
    duration_weeks = forms.TypedChoiceField(choices=DURATION_CHOICES, coerce=int)
    supervisor = forms.ChoiceField(choices=[])

    class Meta:
        model = Classroom
        fields = ["classroom_id", "course_id", "duration_weeks", "supervisor",
                  "building", "room", "online_link"]
        widgets = {
            "classroom_id": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. CLS-001"}),
            "course_id": forms.Select(attrs={"class": "form-select"}),
            "duration_weeks": forms.Select(attrs={"class": "form-select"}),
            "supervisor": forms.Select(attrs={"class": "form-select"}),
            "building": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Building A"}),
            "room": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Room 203"}),
            "online_link": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        preselected_course = kwargs.pop("preselected_course", None)
        super().__init__(*args, **kwargs)

        qs = Course.objects.all()
        if request and getattr(request.user, "role", None) == "INSTRUCTOR":
            qs = qs.filter(instructor=request.user)
        self.fields["course_id"].queryset = qs

        instructors = User.objects.filter(role="INSTRUCTOR").order_by("email")
        choices = [("", "Select Supervisor")]
        choices += list(instructors.values_list("email", "email"))
        self.fields["supervisor"].choices = choices

        if preselected_course:
            self.fields["course_id"].initial = preselected_course.pk

class EditClassroomForm(forms.ModelForm):
    supervisor = forms.ChoiceField(choices=[])
    class Meta:
        model = Classroom
        fields = ["classroom_id", "course_id", "duration_weeks", "supervisor",
                  "building", "room", "online_link"]
        widgets = {
            "classroom_id": forms.TextInput(attrs={"class": "form-control"}),
            "course_id": forms.Select(attrs={"class": "form-select"}),
            "duration_weeks": forms.Select(attrs={"class": "form-select"}),
            "supervisor": forms.Select(attrs={"class": "form-select"}),
            "building": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Building A"}),
            "room": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Room 203"}),
            "online_link": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
        }
        

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        instructors = User.objects.filter(role="INSTRUCTOR").order_by("email")
        choices = [("", "Select Supervisor")]
        choices += list(instructors.values_list("email", "email"))
        self.fields["supervisor"].choices = choices
        self.fields["course_id"].disabled = True
        self.fields["duration_weeks"].disabled = True
