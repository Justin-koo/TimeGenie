from django import forms
from .models import *

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
        fields = ['intake_code', 'total_students', 'sections', 'status']

class TimetableForm(forms.ModelForm):
    class Meta:
        model = Timetable
        fields = ['timetable_profile']