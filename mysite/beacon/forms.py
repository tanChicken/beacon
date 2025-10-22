from django.utils import timezone
from django import forms
from .models import Course, StudentChecklistItem, User, StudentProfile, Instructor, Lesson, Classroom, LessonTask, LessonClassroomAllocation
from .models import Course, LessonClassroomAllocation, StudentChecklistItem, User, StudentProfile, Instructor, Lesson, Classroom, LessonTask
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.db import models
from django.utils import timezone

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
        fields = ["title", "status", "instructor"]
        widgets = {
            "course_id": forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Course Title"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields["course_id"] = forms.CharField(
                initial=self.instance.course_id,
                disabled=True,
                required=False,
                label="Course ID",
                widget=forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"})
            )

class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ["title"]

LessonFormSet = inlineformset_factory(
    Course, Lesson, form=LessonForm, extra=1, can_delete=False
)

class LessonDetailForm(forms.ModelForm):
    designer = forms.ModelChoiceField(
        queryset=Instructor.instructor.all(),
        required=True,
        label="Lesson Designer",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = Lesson
        fields = ['status', 'lesson_id', 'title', 'credit_point', 'description', 'objective', 'prerequisites', 'effort_per_week', 'designer']
        widgets = {
            "lesson_id": forms.TextInput(attrs={"class": "form-control", "readonly":"readonly"}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Lesson Title"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Write a short description"}),
            "objective": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Learning objectives"}),
            "effort_per_week": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Hours per week"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "credit_point": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 30}),
            "prerequisites": forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        self.course = kwargs.pop("course", None)
        self.instance = kwargs.get("instance", None)
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields['description'].required = True
            self.fields['objective'].required = True

        if self.course:
            self.fields["prerequisites"].queryset = Lesson.objects.filter(
                course=self.course,
                status="PUBLISHED"
            ).exclude(pk=self.instance.pk if self.instance else None)

            # If no published lessons exist, hide the prerequisites field
            if not self.fields["prerequisites"].queryset.exists():
                del self.fields["prerequisites"]

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

            if self.instance and self.instance.status in ["PUBLISHED", "ARCHIVED"]:
                for field in self.fields.values():
                    field.disabled = True

    def clean_lesson_id(self):
        lesson_id = self.cleaned_data.get("lesson_id")
        if lesson_id and Lesson.objects.filter(lesson_id=lesson_id).exists():
            if self.instance and self.instance.lesson_id == lesson_id:
                return lesson_id
            raise forms.ValidationError("This lesson ID already exists. Please choose a different one.")
        return lesson_id
    
    def clean_credit_point(self):
        credit_point = self.cleaned_data.get("credit_point", 0)

        if self.course:
            total_existing = (
                Lesson.objects.filter(course=self.course)
                .exclude(pk=self.instance.pk if self.instance else None)
                .aggregate(total=models.Sum("credit_point"))["total"] or 0
            )
        else:
            total_existing = 0

        total_after = total_existing + credit_point
        if total_after > 30:
            raise forms.ValidationError(
                f"Credit points cannot exceed 30 for all lessons in this course."
            )
        return credit_point

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
        
class ChecklistItemForm(forms.ModelForm):
    class Meta:
        model = StudentChecklistItem
        fields = ["title"]

class ClassroomForm(forms.ModelForm):
    supervisor = forms.ChoiceField(choices=[])

    class Meta:
        model = Classroom
        fields = ["course_id", "supervisor","building", "room", "online_link"]
        widgets = {
            "classroom_id": forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"}),
            "course_id": forms.Select(attrs={"class": "form-select"}),
            "supervisor": forms.Select(attrs={"class": "form-select"}),
            "schedule": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Monday 9:00 am - 11:00 am"}),
            "building": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., A"}),
            "room": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., 203"}),
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

class BaseLessonAllocationFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        today = timezone.now().date()

        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            # Skip deleted or empty forms
            if not form.cleaned_data or form.cleaned_data.get('DELETE'):
                continue

            expiry = form.cleaned_data.get('expiry_date')
            if expiry and expiry < today:
                form.add_error('expiry_date', '❌ Expiry date cannot be before today.')
                # You can raise a general formset-level error too:
                raise ValidationError("❌ Cannot save classroom — expiry date is before today.")

class EditClassroomForm(forms.ModelForm):
    supervisor = forms.ChoiceField(choices=[])
    period_weeks = forms.ChoiceField(choices=LessonClassroomAllocation.PERIOD_CHOICES, required=False)
    schedule = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Monday 10AM - 12PM"}))

    class Meta:
        model = Classroom
        fields = [
            "classroom_id", "course_id", "supervisor",
            "building", "room", "online_link",
        ]
        widgets = {
            "classroom_id": forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"}),
            "course_id": forms.Select(attrs={"class": "form-select"}),
            "supervisor": forms.Select(attrs={"class": "form-select"}),
            "building": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., A"}),
            "room": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., 203"}),
            "online_link": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Populate supervisor choices
        instructors = User.objects.filter(role="INSTRUCTOR").order_by("email")
        choices = [("", "Select Supervisor")] + list(instructors.values_list("email", "email"))
        self.fields["supervisor"].choices = choices
        self.fields["course_id"].disabled = True
        self.fields['course_id'].queryset = Course.objects.all()
        self.fields['course_id'].label_from_instance = lambda obj: obj.course_id

class LessonAllocationForm(forms.ModelForm):
    class Meta:
        model = LessonClassroomAllocation
        fields = ["lesson", "period_weeks", "start_date", "expiry_date", "schedule"]
        widgets = {
            "lesson": forms.HiddenInput(),
            "period_weeks": forms.Select(attrs={"class": "form-select"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "expiry_date": forms.DateInput(attrs={"class": "form-control", "type": "date", "readonly": "readonly"}),
            "schedule": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Monday 10:00-12:00"}),
        }

    def __init__(self, *args, **kwargs):
        course = kwargs.pop("course", None)
        super().__init__(*args, **kwargs)

        if course:
            self.fields["lesson"].queryset = Lesson.objects.filter(course=course, status="PUBLISHED").order_by("title")
        else:
            self.fields["lesson"].queryset = Lesson.objects.none()

        # Load existing allocation if instance exists
        if self.instance and self.instance.pk:
            self.fields["period_weeks"].initial = self.instance.period_weeks
            self.fields["schedule"].initial = self.instance.schedule

    def save(self, commit=True):
        allocation = super().save(commit=False)

        # Ensure expiry_date is calculated if not provided
        if not allocation.expiry_date and allocation.start_date and allocation.period_weeks:
            allocation.expiry_date = allocation.start_date + timezone.timedelta(weeks=allocation.period_weeks)

        if commit:
            allocation.save()
        return allocation

class BaseLessonAllocationFormSet(BaseInlineFormSet):
    def save(self, commit=True):
        # Optionally override save logic for the formset
        return super().save(commit=commit)


LessonAllocationFormSet = inlineformset_factory(
    Classroom,
    LessonClassroomAllocation,
    form=LessonAllocationForm,
    formset=BaseLessonAllocationFormSet,
    extra=0,
    can_delete=False,
)

class StudentPasswordChangeForm(forms.Form):
    old_password = forms.CharField(
        label="Current Password",
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )
    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )
    confirm_password = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_old_password(self):
        old_password = self.cleaned_data.get("old_password")
        if not self.user.check_password(old_password):
            raise forms.ValidationError("❌ Your current password is incorrect.")
        return old_password

    def clean(self):
        cleaned_data = super().clean()
        old_password = cleaned_data.get("old_password")
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and old_password and new_password == old_password:
            self.add_error("new_password", "❌ The new password must be different from the current password.")

        if new_password and confirm_password and new_password != confirm_password:
            self.add_error("confirm_password", "❌ The new password and confirmation do not match.")

        return cleaned_data
