from django import forms
from .models import *
from django.contrib.auth.models import User

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name', 'status', 'code']

class ClassForm(forms.ModelForm):
    class Meta:
        model = Classroom
        fields = ['room', 'capacity', 'status']

class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ['section_code', 'section_type', 'section_duration']

    def __init__(self, *args, **kwargs):
        super(SectionForm, self).__init__(*args, **kwargs)
        self.empty_permitted = False

class InstructorForm(forms.ModelForm):
    class Meta:
        model = Instructor
        fields = ['instructor_name', 'status']

class IntakeForm(forms.ModelForm):
    class Meta:
        model = Intake
        fields = ['intake_code', 'sections', 'status']

class TimetableForm(forms.ModelForm):
    class Meta:
        model = Timetable
        fields = ['timetable_profile', 'status']

class StudentForm(forms.ModelForm):
    username = forms.CharField(max_length=150, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.')
    password = forms.CharField(widget=forms.PasswordInput(), required=False)  # Make password optional
    change_password = forms.BooleanField(required=False, label="Change Password")
    name = forms.CharField(max_length=100)
    is_active = forms.ChoiceField(choices=[(1, 'Active'), (0, 'Inactive')], label="Status", required=False)

    class Meta:
        model = StudentProfile
        fields = ['name', 'intake']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(StudentForm, self).__init__(*args, **kwargs)
        if self.user:
            self.fields['username'].initial = self.user.username
            self.fields['name'].initial = self.user.student_profile.name
            self.fields['is_active'].initial = int(self.user.is_active)

    def clean_username(self):
        username = self.cleaned_data['username']
        # Check if self.user is not None and compare usernames or directly filter the queryset
        if self.user and username != self.user.username and User.objects.filter(username=username).exists():
            raise ValidationError("A user with that username already exists.")
        elif not self.user and User.objects.filter(username=username).exists():
            # This handles the case where a new user is being created
            raise ValidationError("A user with that username already exists.")
        return username

    def save(self, commit=True):
        if self.user is None:
            # Create new user
            user = User.objects.create_user(
                username=self.cleaned_data['username'],
                password=self.cleaned_data['password'],
                is_active=bool(int(self.cleaned_data['is_active']))
            )
        else:
            # Update existing user
            user = self.user
            user.username = self.cleaned_data['username']
            user.is_active = bool(int(self.cleaned_data['is_active']))
            # Update the password only if the checkbox is checked
            if self.cleaned_data.get('change_password') and self.cleaned_data.get('password'):
                user.set_password(self.cleaned_data['password'])

        user.save()

        student_profile = super(StudentForm, self).save(commit=False)
        student_profile.user = user
        if commit:
            student_profile.save()
        return student_profile

    