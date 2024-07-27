from collections import defaultdict
from django.http import JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from main.views.views import generate_option_range, generate_time_gap_options, generate_time_options
from ..models import Course, Feedback, InstructorProfile, Section, Timetable, TimetableEntry
from django.core.serializers.json import DjangoJSONEncoder
import json
from ..forms import InstructorForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST

def index(request):
    instructors = InstructorProfile.objects.select_related('user').prefetch_related('sections__course').all()

    for instructor in instructors:
        course_dict = defaultdict(list)
        for section in instructor.sections.all():
            course_dict[section.course].append(section.section_code)
        instructor.course_sections = dict(course_dict)

    return render(request, 'instructor/index.html', {'instructors': instructors, 'local_timezone': timezone.get_current_timezone()})

def create(request):
    courses = Course.objects.all().order_by('name').prefetch_related('sections')
    
    courses_data = []
    for course in courses:
        sections_with_instructor = course.sections.filter(instructor__isnull=True)
        sections_data = list(sections_with_instructor.values('id', 'section_code'))
        
        course_data = {
            'id': course.id,
            'name': course.name,
            'sections': sections_data
        }
        courses_data.append(course_data)

    if request.method == "POST":
        instructor_form = InstructorForm(request.POST)
        if instructor_form.is_valid():
            instructor = instructor_form.save(commit=False)  # Save the form but don't commit to the database yet
            assigned_sections = request.POST.getlist('sections')
            
            instructor.save()  # Now save the instructor to the database
            
            # Update sections if any
            if assigned_sections:
                Section.objects.filter(id__in=assigned_sections).update(instructor=instructor)

            return JsonResponse({'success': True, 'message': 'Instructor has been successfully created!'})
        
        else:
            errors = instructor_form.errors
            return JsonResponse({'success': False, 'errors': errors})

    else:
        instructor_form = InstructorForm()

    context = {
        'courses_json': json.dumps(courses_data, cls=DjangoJSONEncoder),
        'instructor_form': instructor_form
    }

    return render(request, 'instructor/create.html', context)

def edit(request, instructor_id):
    instructor_profile = get_object_or_404(InstructorProfile, id=instructor_id)
    user = instructor_profile.user

    courses = Course.objects.all().order_by('name').prefetch_related('sections')
    
    courses_data = []
    for course in courses:
        sections_data = []
        for section in course.sections.all():
            if section.instructor_id == instructor_profile.id or section.instructor_id is None:
                sections_data.append({'id': section.id, 'section_code': section.section_code})

        course_data = {
            'id': course.id,
            'name': course.name,
            'sections': sections_data
        }
        courses_data.append(course_data)

    associated_sections = list(instructor_profile.sections.values('id', 'section_code'))

    if request.method == 'POST':
        instructor_form = InstructorForm(request.POST, instance=instructor_profile, user=user)

        if instructor_form.is_valid():
            instructor_profile = instructor_form.save(commit=False)

            assigned_sections = request.POST.getlist('sections')

            instructor_profile.save()

            # Clear existing sections for the instructor
            instructor_profile.sections.clear()

            # Add the new sections
            Section.objects.filter(id__in=assigned_sections).update(instructor=instructor_profile)

            return JsonResponse({'success': True, 'message': 'Instructor has been successfully updated!'})

        else:
            errors = instructor_form.errors
            return JsonResponse({'success': False, 'errors': errors})

    else:
        instructor_form = InstructorForm(instance=instructor_profile, user=user)

    context = {
        'courses_json': json.dumps(courses_data, cls=DjangoJSONEncoder),
        'instructor_form': instructor_form,
        'associated_sections': json.dumps(associated_sections, cls=DjangoJSONEncoder),
    }

    return render(request, 'instructor/edit.html', context)

@require_POST
def delete(request, instructor_id):
    try:
        instructor_profile = get_object_or_404(InstructorProfile, id=instructor_id)
    except InstructorProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Instructor not found.'}, status=404)

    # Unassign the sections from the instructor
    Section.objects.filter(instructor=instructor_profile).update(instructor=None)

    # Delete the instructor profile and the associated user
    user = instructor_profile.user
    instructor_profile.delete()
    user.delete()

    return JsonResponse({'success': True, 'message': 'Instructor has been successfully deleted!'})

def is_instructor(user):
    # This is a helper function to check if the user is part of the student group
    return user.groups.filter(name='Instructors').exists()

@login_required
@user_passes_test(is_instructor)
def instructor_dashboard(request):
    instructor_profile = request.user.instructor_profile  # Get the instructor profile

    # Fetch the active timetable for the instructor
    active_timetable = Timetable.objects.filter(timetableentry__instructor_id=instructor_profile.id, status=1).first()

    if active_timetable:
        # Fetch timetable entries for the active timetable of the instructor
        timetable_entries = TimetableEntry.objects.filter(
            timetable=active_timetable,
            instructor_id=instructor_profile.id
        ).select_related('section', 'intake', 'classroom').order_by('day', 'start_time')
    else:
        timetable_entries = []

    # Process and group the data by day
    grouped_instructor_timetable = {}

    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

    for entry in timetable_entries:
        section = entry.section
        classroom = entry.classroom
        intake = entry.intake

        entry_dict = {
            'time': f"{entry.start_time.strftime('%H:%M')} - {entry.end_time.strftime('%H:%M')}",
            'section_code': section.section_code,
            'classroom_name': classroom.room,
            'intake_codes': [intake.intake_code],  # Start with a list of intake codes
        }

        # Group by day
        day = entry.day
        if day not in grouped_instructor_timetable:
            grouped_instructor_timetable[day] = {}

        # Group by time and section
        key = (entry.start_time, entry.end_time, section.section_code, classroom.room)
        if key in grouped_instructor_timetable[day]:
            grouped_instructor_timetable[day][key]['intake_codes'].append(intake.intake_code)
        else:
            grouped_instructor_timetable[day][key] = entry_dict

    # Convert grouped data to the required format
    final_timetable = {}
    for day in day_order:
        if day in grouped_instructor_timetable:
            final_timetable[day] = [
                {
                    'time': f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}",
                    'section_code': data['section_code'],
                    'classroom_name': data['classroom_name'],
                    'intake_codes': ', '.join(data['intake_codes']),
                }
                for (start_time, end_time, section_code, classroom_name), data in grouped_instructor_timetable[day].items()
            ]

    context = {
        'grouped_instructor_timetable': final_timetable,
    }

    return render(request, 'instructor/dashboard.html', context)

@login_required
@user_passes_test(is_instructor)
def instructor_feedback(request):
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

    return render(request, 'instructor/feedback.html', context)