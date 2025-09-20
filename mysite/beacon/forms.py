from django import forms
from .models import Course, StudentReadingListItem, User
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory

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
        fields = ['title', 'description', 'objective', 'effort_per_week', 'assignment', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'objective': forms.Textarea(attrs={'rows': 3}),
            'assignment': forms.Textarea(attrs={'rows': 3}),
        }
        
class ReadingItemForm(forms.ModelForm):
    class Meta:
        model = StudentReadingListItem
        fields = ["title"]