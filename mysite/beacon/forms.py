from django import forms
from .models import Course

class StudentLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["course_id", "title", "status"]