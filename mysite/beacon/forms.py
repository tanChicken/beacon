from django import forms
from .models import Course, StudentReadingListItem, User, StudentProfile, Instructor, Lesson, Classroom
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
        empty_label="Select Instructor"
    )

    class Meta:
        model = Course
        fields = ["course_id", "title", "status", "instructor"]

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
        fields = ['title', 'description', 'objective', 'effort_per_week', 'assignment', 'status', 'lesson_point', 'prerequisites']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'objective': forms.Textarea(attrs={'rows': 3}),
            'assignment': forms.Textarea(attrs={'rows': 3}),
            'prerequisites': forms.CheckboxSelectMultiple,
        }
    lesson_point = forms.IntegerField(
        min_value=0,
        max_value=30,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "min": 0,
            "max": 30
        })
    )

    def __init__(self, *args, **kwargs):
        self.course = kwargs.pop("course", None)
        self.instance = kwargs.get("instance", None)
        super().__init__(*args, **kwargs)

        if self.course:
            self.fields["prerequisites"].queryset = Lesson.objects.filter(course=self.course).exclude(pk=self.instance.pk if self.instance else None)

    def clean_credit_point(self):
        lesson_point = self.cleaned_data.get("lesson_point", 0)

        # Calculate current total
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
        
class ReadingItemForm(forms.ModelForm):
    class Meta:
        model = StudentReadingListItem
        fields = ["title"]

DURATION_CHOICES = [(2, "2 weeks"), (3, "3 weeks"), (4, "4 weeks")]
class ClassroomForm(forms.ModelForm):
    # Force a dropdown with 2/3/4 (stored as int)
    duration_weeks = forms.TypedChoiceField(choices=DURATION_CHOICES, coerce=int)

    # Your model has CharField for supervisor -> make a ChoiceField and fill from instructors
    supervisor = forms.ChoiceField(choices=[])

    class Meta:
        model = Classroom
        fields = ["classroom_id", "course_id", "duration_weeks", "supervisor","building", "room", "online_link"]
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

        # Courses: optionally restrict for instructors to their own courses
        qs = Course.objects.all()
        if request and getattr(request.user, "role", None) == "INSTRUCTOR":
            qs = qs.filter(instructor=request.user)
        self.fields["course_id"].queryset = qs

        # Supervisors: list of instructors; store username (or email) in the CharField
        instructors = User.objects.filter(role="INSTRUCTOR").order_by("email")
        self.fields["supervisor"].choices = list(
            instructors.values_list("email", "email")
        )

        # Preselect course if provided by URL (/course/<pk>/classrooms/new/)
        if preselected_course:
            self.fields["course_id"].initial = preselected_course.pk
            # If you want to lock it, uncomment:
            # self.fields["course_id"].disabled = True

class EditClassroomForm(forms.ModelForm):
    class Meta:
        model = Classroom
        fields = ["classroom_id", "course_id", "duration_weeks", "supervisor","building", "room", "online_link"]
        widgets = {
            "classroom_id": forms.TextInput(attrs={"class": "form-control"}),
            "course_id": forms.Select(attrs={"class": "form-select"}),
            "duration_weeks": forms.Select(attrs={"class": "form-select"}),  # choices on model
            "supervisor": forms.Select(attrs={"class": "form-select"}),

            "building": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Building A"}),
            "room": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Room 203"}),
            "online_link": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Supervisors: list of instructors; store username (or email) in the CharField
        instructors = User.objects.filter(role="INSTRUCTOR").order_by("email")
        self.fields["supervisor"].choices = list(
            instructors.values_list("email", "email")
        )
        # If you want course to be uneditable on edit, uncomment below:
        self.fields["course_id"].disabled = True