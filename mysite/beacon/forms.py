from django import forms
from .models import Course
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class StudentSignupForm(forms.ModelForm):
    title_choices = [
        ('Mr', 'Mr'),
        ('Ms', 'Ms'),
    ]
    title = forms.ChoiceField(choices=title_choices)
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    confirm_password = forms.CharField(widget=forms.PasswordInput, min_length=8)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

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

class StudentLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

class InstructorLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

from .models import Instructor
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

from django.forms import formset_factory

class LessonForm(forms.Form):
    title = forms.CharField(max_length=200)
    credit_points = forms.IntegerField(initial=0, min_value=0)
    status = forms.ChoiceField(choices=[("active","Active"),("inactive","Inactive")])

LessonFormSet = formset_factory(LessonForm, extra=1)