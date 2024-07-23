from collections import defaultdict
import json
import subprocess
import threading
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from main.forms import TimetableForm
from main.ga import GeneticAlgorithm
from main.models import Classroom, Instructor, Intake, Section, Timetable, TimetableEntry
from django.contrib import messages
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth.decorators import login_required

@login_required
def index(request):
    intakes, sections, classrooms = [], [], []

    intakes = Intake.objects.filter(status=1)

    sections = Section.objects.filter(
        course__status=1,
        intakes__in=intakes,
        instructor__status=1
    ).select_related('course', 'instructor').prefetch_related('intakes').distinct()

    classrooms = Classroom.objects.filter(status=1)

    timetable_profiles = Timetable.objects.all()

    context = {
        'intakes': intakes,
        'sections': sections,
        'classrooms': classrooms,
        'timetable_profiles': timetable_profiles,
    }

    return render(request, 'index.html', context)

def save_timetable_to_session(session, student_timetable=None, instructor_schedule=None, class_availability=None, slots=None, status='running'):
    session['ga_status'] = status
    if student_timetable is not None:
        session['student_timetable'] = student_timetable
    if instructor_schedule is not None:
        session['instructor_schedule'] = instructor_schedule
    if class_availability is not None:
        session['class_availability'] = class_availability
    if slots is not None:
        session['slots'] = slots
    session.save()

def check_ga_status(request):
    ga_status = request.session.get('ga_status', 'not_started')
    return JsonResponse({'status': ga_status})

def ga_result(request):
    if not request.session.get('ga_status') == 'completed':
        return redirect('index')

    student_timetable = request.session.get('student_timetable', [])
    instructor_schedule = request.session.get('instructor_schedule', [])
    class_availability = request.session.get('class_availability', [])

    if request.method == 'POST':
        timetable_id = request.POST.get('timetable_id')

        if timetable_id == 'new':
            timetable_form = TimetableForm(request.POST)
            if timetable_form.is_valid():
                timetable = timetable_form.save()
            else:
                errors = timetable_form.errors
                return JsonResponse({'success': False, 'errors': errors})
        else:
            timetable = Timetable.objects.get(id=timetable_id)
            # Clear existing entries for this timetable profile
            TimetableEntry.objects.filter(timetable=timetable).delete()

        slots = request.session.get('slots', [])

        entries = [
            TimetableEntry(
                timetable=timetable,
                intake_id=slot['intake_id'],
                section_id=slot['section_id'],
                instructor_id=slot['instructor_id'],
                classroom_id=slot['classroom_id'],
                start_time=slot['start_time'],
                end_time=slot['end_time'],
                day=slot['day']
            )
            for slot in slots
        ]
        TimetableEntry.objects.bulk_create(entries)

        del request.session['slots']
        del request.session['student_timetable']
        del request.session['instructor_schedule']
        del request.session['class_availability']
        del request.session['ga_status']

        return JsonResponse({'success': True, 'message': 'Profile has been successfully saved!'})

    def sort_entries(entries):
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        entries.sort(key=lambda x: (day_order.index(x['day']), x['time']))
        return entries

    # Fetch related data for student timetable
    for entry in student_timetable:
        intake = Intake.objects.get(id=entry['intake_id'])
        section = Section.objects.get(id=entry['section_id'])
        instructor = Instructor.objects.get(id=section.instructor_id)
        classroom = Classroom.objects.get(id=entry['classroom_id'])
        entry['intake_code'] = intake.intake_code
        entry['section_code'] = section.section_code
        entry['instructor_name'] = instructor.instructor_name
        entry['classroom_name'] = classroom.room

    # Fetch related data for instructor schedule
    for entry in instructor_schedule:
        section = Section.objects.get(id=entry['section_id'])
        instructor = Instructor.objects.get(id=entry['instructor_id'])
        entry['section_code'] = section.section_code
        entry['instructor_name'] = instructor.instructor_name

    # Fetch related data for class availability
    for entry in class_availability:
        section = Section.objects.get(id=entry['section_id'])
        classroom = Classroom.objects.get(id=entry['classroom_id'])
        entry['section_code'] = section.section_code
        entry['classroom_name'] = classroom.room

        student_timetable = sort_entries(student_timetable)
    instructor_schedule = sort_entries(instructor_schedule)
    class_availability = sort_entries(class_availability)

    # Group data
    grouped_student_timetable = {}
    grouped_instructor_schedule = {}
    grouped_class_availability = {}

    for entry in student_timetable:
        intake_code = entry['intake_code']
        if intake_code not in grouped_student_timetable:
            grouped_student_timetable[intake_code] = []
        grouped_student_timetable[intake_code].append(entry)

    for entry in instructor_schedule:
        instructor_name = entry['instructor_name']
        if instructor_name not in grouped_instructor_schedule:
            grouped_instructor_schedule[instructor_name] = []
        grouped_instructor_schedule[instructor_name].append(entry)

    for entry in class_availability:
        classroom_name = entry['classroom_name']
        if classroom_name not in grouped_class_availability:
            grouped_class_availability[classroom_name] = []
        grouped_class_availability[classroom_name].append(entry)

    timetable_profiles = Timetable.objects.all()

    context = {
        'grouped_student_timetable': grouped_student_timetable,
        'grouped_instructor_schedule': grouped_instructor_schedule,
        'grouped_class_availability': grouped_class_availability,
        'timetable_profiles': timetable_profiles
    }

    return render(request, 'timetable/ga_result.html', context)

def ga_view(request):
    intakes, sections, classrooms = [], [], []

    if request.method == "POST":
        error_occurred = False
        error_messages = []

        try:
            intakes = Intake.objects.filter(status=1)
            if not intakes.exists():
                error_messages.append("No active intakes found.")
                error_occurred = True
        except Exception as e:
            error_messages.append(f"Error fetching intakes: {e}")
            error_occurred = True

        try:
            sections = Section.objects.filter(
                course__status=1,
                intakes__in=intakes,
                instructor__status=1
            ).select_related('course', 'instructor').prefetch_related('intakes').distinct()

            if not sections.exists():
                error_messages.append("No active sections found with active instructors.")
                error_occurred = True
        except Exception as e:
            error_messages.append(f"Error fetching sections: {e}")
            error_occurred = True

        try:
            classrooms = Classroom.objects.filter(status=1)
            if not classrooms.exists():
                error_messages.append("No active classrooms found.")
                error_occurred = True
        except Exception as e:
            error_messages.append(f"Error fetching classrooms: {e}")
            error_occurred = True

        if not error_occurred:
            # Calculate the total duration required for all sections in minutes
            total_section_duration = sum(section.section_duration for section in sections)

            # Calculate the total available time slots in all classrooms in minutes
            slots_per_day = 450  # 8:30 AM to 4:00 PM is 7.5 hours, which is 450 minutes
            days_per_week = 5  # Assuming 5 days per week
            total_classroom_slots = len(classrooms) * slots_per_day * days_per_week

            # Check if total available slots are sufficient
            if total_classroom_slots < total_section_duration:
                error_messages.append(f"Not enough total classroom time available to accommodate all sections. Available time: {total_classroom_slots} minutes, Required time: {total_section_duration} minutes.")
                error_occurred = True

            # Check if there is at least one classroom with enough capacity for each section
            for section in sections:
                total_students = sum(intake.total_students for intake in section.intakes.filter(status=1))
                if not any(classroom.capacity >= total_students for classroom in classrooms):
                    error_messages.append(f"No classrooms have enough capacity to accommodate section {section.section_code} with {total_students} students.")
                    error_occurred = True
                    break

        if error_occurred:
            return JsonResponse({'status': 'error', 'messages': error_messages})

        # ga parameter
        # population_size = 100
        # gene_length = len(sections)
        # mutation_rate = 0.1
        # generations = 1

        sections_data = [
            {
                'id': section.id,
                'duration': section.section_duration,
                'course_id': section.course.id,
                'instructor_id': section.instructor.id,
                'intake_ids': [intake.id for intake in section.intakes.filter(status=1)],
                'total_students': sum(intake.total_students for intake in section.intakes.filter(status=1))
            }
            for section in sections
        ]

        classrooms_data = [{'id': classroom.id, 'capacity': classroom.capacity} for classroom in classrooms]

        save_timetable_to_session(request.session, status='running')
        threading.Thread(target=run_ga, args=(sections_data, classrooms_data, request.session)).start()
        return JsonResponse({'status': 'GA started'})

        # ga = GeneticAlgorithm(population_size, gene_length, mutation_rate, sections_data, classrooms_data)

        # while True:
        #     ga.evolve()
        #     best_timetable = max(ga.population, key=lambda x: x.fitness)
        #     ga.best_fitness_history.append(best_timetable.fitness)

        #     print(f"Generation {generations}: Best Fitness = {best_timetable.fitness}")
        #     print(f'Conflict: {best_timetable.conflict}')

        #     if best_timetable.fitness >= 70:
        #         student_timetable = best_timetable.get_student_timetable()
        #         instructor_schedule = best_timetable.get_instructor_schedule()
        #         class_availability = best_timetable.get_class_availability()
        #         return render(request, 'ga_result.html', {
        #             'student_timetable': student_timetable,
        #             'instructor_schedule': instructor_schedule,
        #             'class_availability': class_availability
        #         })
        #         break

        #     generations += 1

def run_ga(sections, classrooms, session):
    population_size = 100
    gene_length = len(sections)
    mutation_rate = 0.1
    max_generations = 1000
    generations = 0

    ga = GeneticAlgorithm(population_size, gene_length, mutation_rate, sections, classrooms)

    channel_layer = get_channel_layer()

    best_timetable = None
    while generations < max_generations:
        ga.evolve()
        best_timetable = max(ga.population, key=lambda x: x.fitness)
        ga.best_fitness_history.append(best_timetable.fitness)

        async_to_sync(channel_layer.group_send)(
            "ga_progress",
            {
                "type": "send_progress",
                "message": {
                    "generation": generations,
                    "best_fitness": best_timetable.fitness,
                    "conflict": best_timetable.conflict,
                }
            }
        )

        if best_timetable.fitness >= 0.7:

            slots = best_timetable.get_all_slots()

            student_timetable = best_timetable.get_student_timetable()
            instructor_schedule = best_timetable.get_instructor_schedule()
            class_availability = best_timetable.get_class_availability()

            save_timetable_to_session(session, student_timetable, instructor_schedule, class_availability, slots, status='completed')

            result = {
                'student_timetable': student_timetable,
                'instructor_schedule': instructor_schedule,
                'class_availability': class_availability,
                'completed': True
            }

            async_to_sync(channel_layer.group_send)(
                "ga_progress",
                {
                    "type": "send_progress",
                    "message": result
                }
            )
            break

        generations += 1

    if generations == max_generations and best_timetable:
        slots = best_timetable.get_all_slots()

        student_timetable = best_timetable.get_student_timetable()
        instructor_schedule = best_timetable.get_instructor_schedule()
        class_availability = best_timetable.get_class_availability()

        save_timetable_to_session(session, student_timetable, instructor_schedule, class_availability, slots, status='completed')

        result = {
            'student_timetable': student_timetable,
            'instructor_schedule': instructor_schedule,
            'class_availability': class_availability,
            'completed': False
        }

        async_to_sync(channel_layer.group_send)(
            "ga_progress",
            {
                "type": "send_progress",
                "message": result
            }
        )
        
    return best_timetable
