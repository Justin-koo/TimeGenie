from collections import defaultdict
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render

from main.views.views import generate_option_range, generate_time_gap_options, generate_time_options
from ..models import Course, Feedback, InstructorProfile, Intake, Section, StudentProfile, TimetableEntry, Timetable
from django.core.serializers.json import DjangoJSONEncoder
import json
from ..forms import InstructorForm, StudentForm
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, user_passes_test

def index(request):
    students = User.objects.filter(student_profile__isnull=False).select_related('student_profile', 'student_profile__intake')

    return render(request, 'student/index.html', {'students': students, 'local_timezone': timezone.get_current_timezone()})

def create(request):
    intakes = Intake.objects.filter(status=1)

    if request.method == "POST":
        student_form = StudentForm(request.POST)

        if student_form.is_valid():
            student_form.save()

            return JsonResponse({'success': True, 'message': 'Student has been successfully created!'})
        
        else:
            errors = student_form.errors
            return JsonResponse({'success': False, 'errors': errors})

    else:
        student_form = StudentForm()
    context = {
        'intakes': intakes,
        'student_form': student_form
    }

    return render(request, 'student/create.html', context)

def edit(request, student_id):
    try: 
        user = get_object_or_404(User, pk=student_id)
    except Http404:
        messages.error(request, 'Student not found')
        return redirect('student.index')
    
    student_profile = user.student_profile
    intakes = Intake.objects.filter(status=1)

    if request.method == 'POST':
        student_form = StudentForm(request.POST, instance=student_profile, user=user)

        if student_form.is_valid():
            student_form.save()

            return JsonResponse({'success': True, 'message': 'Student has been successfully updated!'})

        else:
            errors = student_form.errors
            return JsonResponse({'success': False, 'errors': errors})

    else:
        student_form = StudentForm(instance=student_profile, user=user)

    context = {
        'intakes': intakes,
        'student_form': student_form,
    }

    return render(request, 'student/edit.html', context)

@require_http_methods(["POST"]) 
def delete(request, student_id):
    if request.user.is_superuser or request.user.id == int(student_id):
        try:
            user = User.objects.get(pk=student_id)
            user.delete()  # Deleting the User also deletes the StudentProfile due to CASCADE
            return JsonResponse({'success': True, 'message': 'User deleted successfully.'})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User not found.'}, status=404)
    else:
        return JsonResponse({'success': False, 'message': 'Unauthorized access.'}, status=403)
    
def is_student(user):
    # This is a helper function to check if the user is part of the student group
    return user.groups.filter(name='Students').exists()

@login_required
@user_passes_test(is_student)
def student_dashboard(request):
    student_profile = request.user.student_profile
    intake = student_profile.intake  # Get the intake from the student's profile

    # Fetch the active timetable for the student's intake
    active_timetable = Timetable.objects.filter(timetableentry__intake_id=intake.id, status=1).first()

    if active_timetable:
        # Fetch timetable entries for the active timetable of the student's intake
        timetable_entries = TimetableEntry.objects.filter(
            timetable=active_timetable,
            intake_id=intake.id
        ).select_related('section', 'instructor', 'classroom').order_by('day', 'start_time')
    else:
        timetable_entries = []

    # Process and group the data by day
    grouped_student_timetable = {}

    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

    for entry in timetable_entries:
        section = entry.section
        classroom = entry.classroom
        instructor = entry.instructor

        entry_dict = {
            'time': f"{entry.start_time.strftime('%H:%M')} - {entry.end_time.strftime('%H:%M')}",
            'section_code': section.section_code,
            'classroom_name': classroom.room,
            'instructor_name': instructor.instructor_name,  # Include the instructor's name
        }

        # Group by day
        day = entry.day
        if day not in grouped_student_timetable:
            grouped_student_timetable[day] = []
        grouped_student_timetable[day].append(entry_dict)

    # Ensure the days are in order
    grouped_student_timetable = {day: grouped_student_timetable.get(day, []) for day in day_order if day in grouped_student_timetable}

    context = {
        'grouped_student_timetable': grouped_student_timetable,
        'intake_code': intake.intake_code  # Include the intake code in the context
    }

    return render(request, 'student/dashboard.html', context)

@login_required
@user_passes_test(is_student)
def student_feedback(request):
    start_times = generate_time_options(8, 30, 10, 30, 15)  # From 8:30 AM to 5:00 PM in 15-minute intervals
    end_times = generate_time_options(16, 00, 18, 0, 15, descending=True)  # From 8:30 AM to 6:00 PM in 15-minute intervals
    max_time_gaps = generate_time_gap_options(60, 120, 15)
    min_time_gaps = generate_time_gap_options(15, 45, 15)
    lunch_duration = generate_time_gap_options(30, 60, 15)
    lunch_times = generate_time_options(12, 0, 13, 0, 15) 
    min_classes_per_day = generate_option_range(1, 2, 1) 

    user = request.user

    if request.method == 'POST':
        start_time_rank = request.POST.get('start_time_rank')
        end_time_rank = request.POST.get('end_time_rank')
        max_time_gap_rank = request.POST.get('max_time_gap_rank')
        min_time_gap_rank = request.POST.get('min_time_gap_rank')
        lunch_start_rank = request.POST.get('lunch_start_rank')
        lunch_duration_rank = request.POST.get('lunch_duration_rank')
        delayed_lunch_start_rank = request.POST.get('delayed_lunch_start_rank')
        min_classes_per_day_rank = request.POST.get('min_classes_per_day_rank')

        if not all([
            start_time_rank, end_time_rank, max_time_gap_rank,
            min_time_gap_rank, lunch_start_rank, lunch_duration_rank,
            delayed_lunch_start_rank, min_classes_per_day_rank
        ]):
            errors = {
                'start_time_rank': 'This field is required.' if not start_time_rank else '',
                'end_time_rank': 'This field is required.' if not end_time_rank else '',
                'max_time_gap_rank': 'This field is required.' if not max_time_gap_rank else '',
                'min_time_gap_rank': 'This field is required.' if not min_time_gap_rank else '',
                'lunch_start_rank': 'This field is required.' if not lunch_start_rank else '',
                'lunch_duration_rank': 'This field is required.' if not lunch_duration_rank else '',
                'delayed_lunch_start_rank': 'This field is required.' if not delayed_lunch_start_rank else '',
                'min_classes_per_day_rank': 'This field is required.' if not min_classes_per_day_rank else '',
            }
            return JsonResponse({'success': False, 'errors': errors})

        feedback, created = Feedback.objects.update_or_create(
            user=user,
            defaults={
                'start_time_rank': start_time_rank,
                'end_time_rank': end_time_rank,
                'max_time_gap_rank': max_time_gap_rank,
                'min_time_gap_rank': min_time_gap_rank,
                'lunch_start_rank': lunch_start_rank,
                'lunch_duration_rank': lunch_duration_rank,
                'delayed_lunch_start_rank': delayed_lunch_start_rank,
                'min_classes_per_day_rank': min_classes_per_day_rank
            }
        )
        
        return JsonResponse({'success': True, 'message': 'Feedback submitted successfully.'})
    
    feedback = Feedback.objects.filter(user=user).first()
    preferences = {}

    if feedback:
        preferences = {
            'start_time_rank': feedback.start_time_rank,
            'end_time_rank': feedback.end_time_rank,
            'max_time_gap_rank': feedback.max_time_gap_rank,
            'min_time_gap_rank': feedback.min_time_gap_rank,
            'lunch_start_rank': feedback.lunch_start_rank,
            'lunch_duration_rank': feedback.lunch_duration_rank,
            'delayed_lunch_start_rank': feedback.delayed_lunch_start_rank,
            'min_classes_per_day_rank': feedback.min_classes_per_day_rank
        }
    else:
        preferences = {
            'start_time_rank': 510,
            'end_time_rank': 1080,
            'max_time_gap_rank': 60,
            'min_time_gap_rank': 15,
            'lunch_start_rank': 720,
            'lunch_duration_rank': 30,
            'delayed_lunch_start_rank': 30,
            'min_classes_per_day_rank': 1
        }
    
    context = {
        'start_times': start_times,
        'end_times': end_times,
        'max_time_gaps': max_time_gaps,
        'min_time_gaps': min_time_gaps,
        'lunch_duration': lunch_duration,
        'lunch_times': lunch_times,
        'min_classes_per_day': min_classes_per_day,
        'preferences': preferences
    }

    return render(request, 'student/feedback.html', context)