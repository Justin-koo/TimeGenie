from django.conf import settings
from django.db import models
from django.forms import ValidationError
from django.utils import timezone
from django.db.models.functions import Lower
from django.db.models import UniqueConstraint
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, User

class Course(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    status = models.IntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'courses'

    def clean(self):
        if Course.objects.filter(name__iexact=self.name).exclude(pk=self.pk).exists():
            raise ValidationError({'name': "A course with this name already exists."})  # Ensure error message is a list
        super().clean()

    def __str__(self):
        return self.name
    
class InstructorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='instructor_profile')
    instructor_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'instructor_profile'

    def __str__(self):
        return self.instructor_name 

class Section(models.Model):
    course = models.ForeignKey(Course, related_name='sections', on_delete=models.CASCADE)
    instructor = models.ForeignKey(InstructorProfile, related_name='sections', on_delete=models.SET_NULL, null=True, blank=True)
    section_code = models.CharField(max_length=20, unique=True)
    section_type = models.CharField(max_length=10)
    section_duration = models.IntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sections'

    def clean(self):
        if Section.objects.filter(section_code__iexact=self.section_code).exclude(pk=self.pk).exists():
            raise ValidationError({'section_code': "A section with this code already exists."})
        super().clean()

    def __str__(self):
        return f"{self.section_code}"
    
class Classroom(models.Model):
    room = models.CharField(max_length=20)
    capacity = models.IntegerField(default=0)
    status = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'classrooms'
        constraints = [
            models.UniqueConstraint(fields=['room'], name='unique_room')
        ]

    def clean(self):
        if Classroom.objects.filter(room__iexact=self.room).exclude(pk=self.pk).exists():
            raise ValidationError({'room': "A classroom with this room name already exists."})
        super().clean()

    def __str__(self):
        return self.room
    
class Intake(models.Model):
    intake_code = models.CharField(max_length=20, unique=True)
    # total_students = models.IntegerField(default=0)
    status = models.IntegerField(default=0)
    sections = models.ManyToManyField(Section, related_name='intakes', blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'intakes'
        constraints = [
            models.UniqueConstraint(fields=['intake_code'], name='unique_intake_code')
        ]

    def clean(self):
        if Intake.objects.filter(intake_code__iexact=self.intake_code).exclude(pk=self.pk).exists():
            raise ValidationError({'intake_code': "A intake code with this name already exists."})
        super().clean()

    def __str__(self):
        return self.intake_code
    
class Timetable(models.Model):
    timetable_profile = models.CharField(max_length=20, unique=True)
    status = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'timetable'
        constraints = [
            models.UniqueConstraint(fields=['timetable_profile'], name='unique_timetable_profile')
        ]

    def clean(self):
        if Timetable.objects.filter(timetable_profile__iexact=self.timetable_profile).exclude(pk=self.pk).exists():
            raise ValidationError({'timetable_profile': "A profile with this name already exists."})
        super().clean()

class TimetableEntry(models.Model):
    timetable = models.ForeignKey(Timetable, on_delete=models.CASCADE)
    intake = models.ForeignKey(Intake, on_delete=models.PROTECT)  # Link to the Intake model
    section = models.ForeignKey(Section, on_delete=models.PROTECT)
    instructor = models.ForeignKey(InstructorProfile, on_delete=models.PROTECT)
    classroom = models.ForeignKey(Classroom, on_delete=models.PROTECT)
    start_time = models.TimeField()
    end_time = models.TimeField()
    day = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'timetable_entry'

class StudentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    name = models.CharField(max_length=100)
    intake = models.ForeignKey(Intake, on_delete=models.SET_NULL, null=True, related_name='students')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'student_profile'

    def __str__(self):
        return self.user.username    
    
class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time_rank = models.IntegerField()
    end_time_rank = models.IntegerField()
    max_time_gap_rank = models.IntegerField()
    min_time_gap_rank = models.IntegerField()
    lunch_start_rank = models.IntegerField()
    lunch_duration_rank = models.IntegerField()
    delayed_lunch_start_rank = models.IntegerField()
    min_classes_per_day_rank = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'feedback'