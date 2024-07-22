from django.db import models
from django.forms import ValidationError
from django.utils import timezone

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
    
class Instructor(models.Model):
    instructor_name = models.CharField(max_length=100)
    status = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'instructors'

    def __str__(self):
        return self.instructor_name 

class Section(models.Model):
    course = models.ForeignKey(Course, related_name='sections', on_delete=models.CASCADE)
    instructor = models.ForeignKey(Instructor, related_name='sections', on_delete=models.SET_NULL, null=True, blank=True)
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
    intake_code = models.CharField(max_length=20)
    total_students = models.IntegerField(default=0)
    status = models.IntegerField(default=0)
    sections = models.ManyToManyField(Section, related_name='intakes', blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'intakes'

    def __str__(self):
        return self.intake_code
    
class Timetable(models.Model):
    timetable_profile = models.CharField(max_length=20, unique=True)
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
    intake_id = models.IntegerField()
    section_id = models.IntegerField()
    instructor_id = models.IntegerField()
    classroom_id = models.IntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    day = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'timetable_entry'
        