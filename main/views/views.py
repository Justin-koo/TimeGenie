from collections import defaultdict
from functools import partial
import json
import subprocess
import threading
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
import numpy as np
from main.forms import TimetableForm
from main.ga import GeneticAlgorithm
import pygad
from main.models import Classroom, InstructorProfile, Intake, Section, Timetable, TimetableEntry
from django.contrib import messages
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.serializers.json import DjangoJSONEncoder
from django.views.decorators.http import require_http_methods
from django.contrib.auth.views import LoginView
from django.db.models import Count, Q

timeslots = [
        510,   # 8:30 AM
        525,   # 8:45 AM
        540,   # 9:00 AM
        555,   # 9:15 AM
        570,   # 9:30 AM
        585,   # 9:45 AM
        600,   # 10:00 AM
        615,   # 10:15 AM
        630,   # 10:30 AM
        645,   # 10:45 AM
        660,   # 11:00 AM
        675,   # 11:15 AM
        690,   # 11:30 AM
        705,   # 11:45 AM
        720,   # 12:00 PM
        735,   # 12:15 PM
        750,   # 12:30 PM
        765,   # 12:45 PM
        780,   # 1:00 PM 
        795,   # 1:15 PM 
        810,   # 1:30 PM 
        825,   # 1:45 PM 
        840,   # 2:00 PM 
        855,   # 2:15 PM 
        870,   # 2:30 PM 
        885,   # 2:45 PM
        900,   # 3:00 PM
        915,   # 3:15 PM
        930,   # 3:30 PM
        945,   # 3:45 PM
        960,   # 4:00 PM
    ]

def index(request):
    intakes, sections, classrooms = [], [], []

    intakes = Intake.objects.prefetch_related('sections__course').annotate(
        active_student_count=Count('students', filter=Q(students__user__is_active=True))
    ).filter(active_student_count__gt=0)

    sections = Section.objects.filter(
        course__status=1,
        intakes__in=intakes,
        instructor__user__is_active=True  # Filter based on the is_active field in auth_user
    ).select_related('course', 'instructor__user').prefetch_related('intakes').distinct()

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
        status = int(request.POST.get('status', 0))

        if not timetable_id:
            return JsonResponse({'success': False, 'errors': {'timetable_id': 'No timetable profile selected.'}})

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

        if status == 1:
            Timetable.objects.exclude(id=timetable.id).update(status=0)

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
        instructor = InstructorProfile.objects.get(id=section.instructor_id)
        classroom = Classroom.objects.get(id=entry['classroom_id'])
        entry['intake_code'] = intake.intake_code
        entry['section_code'] = section.section_code
        entry['instructor_name'] = instructor.instructor_name
        entry['classroom_name'] = classroom.room

    # Fetch related data for instructor schedule
    for entry in instructor_schedule:
        section = Section.objects.get(id=entry['section_id'])
        instructor = InstructorProfile.objects.get(id=entry['instructor_id'])
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

@require_http_methods(["POST"])
def ga_view(request):
    intakes, sections, classrooms = [], [], []

    error_occurred = False
    error_messages = []

    try:
        # Annotate intakes with the count of active students
        intakes = Intake.objects.prefetch_related('sections__course').annotate(
            active_student_count=Count('students', filter=Q(students__user__is_active=True))
        ).filter(active_student_count__gt=0)

        if not intakes.exists():
            error_messages.append("No active intakes with students found.")
            error_occurred = True
    except Exception as e:
        error_messages.append(f"Error fetching intakes: {e}")
        error_occurred = True

    try:
        sections = Section.objects.filter(
            course__status=1,
            intakes__in=intakes,
            instructor__user__is_active=True  # Filter based on the is_active field in auth_user
        ).select_related('course', 'instructor__user').prefetch_related('intakes').distinct()

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
            total_students = sum(intake.students.filter(user__is_active=True).count() for intake in section.intakes.filter(status=1))
            if not any(classroom.capacity >= total_students for classroom in classrooms):
                error_messages.append(f"No classrooms have enough capacity to accommodate section {section.section_code} with {total_students} students.")
                error_occurred = True
                break

    if error_occurred:
        return JsonResponse({'status': 'error', 'messages': error_messages})

    sections_data = [
        {
            'id': section.id,
            'duration': section.section_duration,
            'course_id': section.course.id,
            'instructor_id': section.instructor.id,
            'intake_ids': [intake.id for intake in section.intakes.filter(status=1).annotate(active_student_count=Count('students', filter=Q(students__user__is_active=True))).filter(active_student_count__gt=0)],
            'total_students': sum(intake.students.filter(user__is_active=True).count() for intake in section.intakes.filter(status=1))
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

    classroom_capacity_map = {classroom['id']: classroom['capacity'] for classroom in classrooms}

    ensure_default_preferences(session)
    preferences = session['ga_preferences']
    lunch_end = preferences['lunch_start'] + preferences['lunch_duration']
    lunch_break = (preferences['lunch_start'], lunch_end)
    lunch_duration = preferences['lunch_duration']

    gene_length = len(sections)
    population_size = preferences['population_size']
    max_generations = preferences['max_generations']

    initial_population = create_initial_population(population_size, sections, classroom_capacity_map)

    def random_mutation(offspring, ga_instance):
        mutation_probability = 0.1

        for idx in range(offspring.shape[0]):
            if np.random.rand() < mutation_probability:
                # Select a random gene in the offspring
                gene_idx = np.random.randint(0, offspring.shape[1] // 3) * 3

                # Perform mutation within the constraints
                day = np.random.randint(0, 5)
                timeslot_idx = np.random.randint(0, len(timeslots))
                room = np.random.choice(list(classroom_capacity_map.keys()))

                # Update the gene with the new values
                offspring[idx, gene_idx:gene_idx + 3] = [day, timeslot_idx, room]

        return offspring

    def fitness_function(ga, solution, solution_idx):
        penalty = 0

        # Decode the solution
        timetable = np.reshape(solution, (gene_length, 3))

        # Dictionary to track room and intake usage
        room_usage = {day: {room: [] for room in list(classroom_capacity_map.keys())} for day in range(5)}
        intake_ids = set(intake for section in sections for intake in section['intake_ids'])
        instructor_ids = set(section['instructor_id'] for section in sections)
        
        intake_usage = {intake: {day: [] for day in range(5)} for intake in intake_ids}
        instructor_usage = {instructor: {day: [] for day in range(5)} for instructor in instructor_ids}
        
        # Check for room capacity violations and overlapping courses
        for section_idx, section in enumerate(timetable):
            day, timeslot_idx, room = section

            start_time = timeslots[timeslot_idx]
            current_section = sections[section_idx]
            duration = current_section['duration']
            end_time = start_time + int(duration)
            
            # Room capacity violation check
            if current_section['total_students'] > classroom_capacity_map[room]:
                penalty += 1
            
            # Intake classes overlap check
            for intake in current_section['intake_ids']:
                for (other_start_time, other_end_time) in intake_usage[intake][day]:
                    if (start_time < other_end_time) and (end_time > other_start_time):
                        penalty += 1
            
            # Overlapping courses check within the same room
            for (other_start_time, other_end_time) in room_usage[day][room]:
                if (start_time < other_end_time) and (end_time > other_start_time):
                    penalty += 1
            
            # Instructor overlap check
            instructor = current_section['instructor_id']
            for (other_start_time, other_end_time) in instructor_usage[instructor][day]:
                if (start_time < other_end_time) and (end_time > other_start_time):
                    penalty += 1
            
            # Add the current course time slot to the room and intake usage
            room_usage[day][room].append((start_time, end_time))
            for intake_id in current_section['intake_ids']:
                intake_usage[intake_id][day].append((start_time, end_time))
            instructor_usage[instructor][day].append((start_time, end_time))

        # Soft constraint: Check the earliest start time for each intake and day
        for intake, days in intake_usage.items():
            for day, times in days.items():
                if times:
                    sorted_times = sorted(times)

                    earliest_start_time = sorted_times[0][0]
                    if earliest_start_time < preferences['start_time']:
                        # penalty +=1
                        penalty += (preferences['start_time'] - earliest_start_time) / 60.0 / 5

                    last_end_time = sorted_times[-1][1]
                    if last_end_time > preferences['end_time']:
                        # penalty +=1
                        penalty += (last_end_time - preferences['end_time']) / 60.0 / 5

                    total_times = len(sorted_times)

                    if total_times < preferences['min_classes_per_day']:
                        penalty += 1

                    for i in range(total_times):
                        start_time = sorted_times[i][0]
                        end_time = sorted_times[i][1]

                        if (start_time <= lunch_break[0] and end_time >= lunch_break[1]) or (start_time >= lunch_break[0] and start_time < lunch_break[1]) or (end_time >= lunch_break[0] and end_time <= lunch_break[1]):
                            if end_time >= lunch_break[0] + preferences['delayed_lunch_start']:
                                # penalty += 1
                                penalty += (end_time - lunch_break[0] + preferences['delayed_lunch_start']) / 60.0 / 5 
                            
                            if i < total_times - 1:
                                next_start_time = sorted_times[i + 1][0]
                                gap = next_start_time - end_time
                                if not (gap >= lunch_duration):
                                    # penalty += 1
                                    penalty += (lunch_duration - gap) / 60.0 / 5
                                else:
                                    if (gap > preferences['max_time_gap']):
                                        # penalty += 1
                                        penalty += (gap - preferences['max_time_gap']) / 60.0 / 5

                        else:
                            if i < total_times - 1:
                                next_start_time = sorted_times[i + 1][0]
                                gap = next_start_time - end_time

                                if gap > preferences['max_time_gap']:
                                    penalty += (gap - preferences['max_time_gap']) / 60.0 / 5

                                if gap <= preferences['min_time_gap']:
                                    penalty += (preferences['min_time_gap'] - gap) / 60.0 / 5

                                # if gap > preferences['max_time_gap'] or gap <= preferences['min_time_gap']:
                                #     penalty += 1

        for _, days in instructor_usage.items():
            for day, times in days.items():
                if times:
                    sorted_times = sorted(times)

                    total_times = len(sorted_times)

                    for i in range(total_times):
                        start_time = sorted_times[i][0]
                        end_time = sorted_times[i][1]

                        if (start_time <= lunch_break[0] and end_time >= lunch_break[1]) or (start_time >= lunch_break[0] and start_time < lunch_break[1]) or (end_time >= lunch_break[0] and end_time <= lunch_break[1]):
                            if end_time >= lunch_break[0] + preferences['delayed_lunch_start']:
                                # penalty += 1
                                penalty += (end_time - lunch_break[0] + preferences['delayed_lunch_start']) / 60.0 / 5 
                            
                            if i < total_times - 1:
                                next_start_time = sorted_times[i + 1][0]
                                gap = next_start_time - end_time
                                if not (gap >= lunch_duration):
                                    # penalty += 1
                                    penalty += (lunch_duration - gap) / 60.0 / 5
                                else:
                                    if (gap > preferences['max_time_gap']):
                                        # penalty += 1
                                        penalty += (gap - preferences['max_time_gap']) / 60.0 / 5

                        else:
                            if i < total_times - 1:
                                next_start_time = sorted_times[i + 1][0]
                                gap = next_start_time - end_time

                                if gap > preferences['max_time_gap']:
                                    penalty += (gap - preferences['max_time_gap']) / 60.0 / 5

                                if gap <= preferences['min_time_gap']:
                                    penalty += (preferences['min_time_gap'] - gap) / 60.0 / 5

                                # if gap > preferences['max_time_gap'] or gap <= preferences['min_time_gap']:
                                #     penalty += 1

        # Calculate the fitness value
        fitness = 1.0 / (1.0 + penalty)
        return fitness

    ga_instance = pygad.GA(
        num_generations=max_generations,
        num_parents_mating=int(0.1 * population_size),
        fitness_func=fitness_function,
        initial_population=initial_population,
        parent_selection_type='tournament',
        crossover_type='uniform',
        # mutation_type='swap',
        mutation_type=random_mutation,
        # mutation_probability=0.5,
        # gene_space=gene_space,
        # random_seed=123,
        gene_type=int,
        on_generation=on_gen,
        keep_elitism=int(0.1 * population_size),
        stop_criteria=[
            "reach_0.7", 
            # "saturate_100"
            ],
    )

    ga_instance.run()
    solution, solution_fitness, solution_idx = ga_instance.best_solution()

    processor = TimetableProcessor(solution, sections, timeslots)
    instructor_schedule = processor.get_instructor_schedule()
    class_availability = processor.get_class_availability()
    student_timetable = processor.get_student_timetable()
    slots = processor.get_all_slots()

    student_timetable_native = convert_to_native(student_timetable)
    instructor_schedule_native = convert_to_native(instructor_schedule)
    class_availability_native = convert_to_native(class_availability)
    slots_native = convert_to_native(slots)

    save_timetable_to_session(session, student_timetable_native, instructor_schedule_native, class_availability_native, slots_native, status='completed')

    result = {
        "instructor_schedule": instructor_schedule_native,
        "class_availability": class_availability_native,
        "student_timetable": student_timetable_native,
        'completed': True
    }


    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        "ga_progress",
        {
            "type": "send_progress",
            "message": result
        }
    )
    # ga = GeneticAlgorithm(population_size, gene_length, mutation_rate, sections, classrooms)

    # channel_layer = get_channel_layer()

    # best_timetable = None
    # while generations < max_generations:
    #     ga.evolve()
    #     best_timetable = max(ga.population, key=lambda x: x.fitness)
    #     ga.best_fitness_history.append(best_timetable.fitness)

    #     async_to_sync(channel_layer.group_send)(
    #         "ga_progress",
    #         {
    #             "type": "send_progress",
    #             "message": {
    #                 "generation": generations,
    #                 "best_fitness": best_timetable.fitness,
    #                 "conflict": best_timetable.conflict,
    #             }
    #         }
    #     )

    #     if best_timetable.fitness >= 0.7:

    #         slots = best_timetable.get_all_slots()

    #         student_timetable = best_timetable.get_student_timetable()
    #         instructor_schedule = best_timetable.get_instructor_schedule()
    #         class_availability = best_timetable.get_class_availability()

    #         save_timetable_to_session(session, student_timetable, instructor_schedule, class_availability, slots, status='completed')

    #         result = {
    #             'student_timetable': student_timetable,
    #             'instructor_schedule': instructor_schedule,
    #             'class_availability': class_availability,
    #             'completed': True
    #         }

    #         async_to_sync(channel_layer.group_send)(
    #             "ga_progress",
    #             {
    #                 "type": "send_progress",
    #                 "message": result
    #             }
    #         )
    #         break

    #     generations += 1

    # if generations == max_generations and best_timetable:
    #     slots = best_timetable.get_all_slots()

    #     student_timetable = best_timetable.get_student_timetable()
    #     instructor_schedule = best_timetable.get_instructor_schedule()
    #     class_availability = best_timetable.get_class_availability()

    #     save_timetable_to_session(session, student_timetable, instructor_schedule, class_availability, slots, status='completed')

    #     result = {
    #         'student_timetable': student_timetable,
    #         'instructor_schedule': instructor_schedule,
    #         'class_availability': class_availability,
    #         'completed': False
    #     }

    #     async_to_sync(channel_layer.group_send)(
    #         "ga_progress",
    #         {
    #             "type": "send_progress",
    #             "message": result
    #         }
    #     )
        
    # return best_timetable

def create_gene(classroom_capacity_map):
    num_days = 5

    day = np.random.randint(0, num_days)
    timeslot_idx = np.random.randint(0, len(timeslots))
    room = np.random.choice(list(classroom_capacity_map.keys()))
    return [day, timeslot_idx, room]

def create_initial_population(population_size, sections, classroom_capacity_map):
    initial_population = []
    for _ in range(population_size):
        solution = []
        for section in sections:
            solution.extend(create_gene(classroom_capacity_map))
        initial_population.append(solution)
    return np.array(initial_population)

def on_gen(ga_instance):
    generations = ga_instance.generations_completed
    solution, solution_fitness, solution_idx = ga_instance.best_solution()
    # best_fitness = ga_instance.best_solutions_fitness

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "ga_progress",
        {
            "type": "send_progress",
            "message": {
                "generation": generations,
                "best_fitness": solution_fitness,
                # "conflict": best_timetable['conflict'],
            }
        }
    )

class TimetableProcessor:
    def __init__(self, solution, sections, timeslots):
        self.genes = np.reshape(solution, (-1, 3))
        self.sections = sections
        self.timeslots = timeslots

    def convert_minutes_to_time(self, minutes):
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours:02}:{minutes:02}"

    def get_day_name(self, day):
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        return days[day]

    def get_instructor_schedule(self):
        instructor_schedule = defaultdict(lambda: defaultdict(list))
        for idx, gene in enumerate(self.genes):
            day, timeslot_idx, room = gene
            section = self.sections[idx]
            instructor_id = section['instructor_id']

            start_time = self.convert_minutes_to_time(self.timeslots[timeslot_idx])
            end_time = self.convert_minutes_to_time((self.timeslots[timeslot_idx] + section['duration']))
            time_slot_str = f"{start_time} - {end_time}"
            instructor_slot = {'section_id': section['id'], 'time_slot_str': time_slot_str}
            instructor_schedule[instructor_id][day].append(instructor_slot)

        output = []
        for instructor_id, schedule in instructor_schedule.items():
            for day, entries in schedule.items():
                day_name = self.get_day_name(day)
                for entry in entries:
                    output.append({
                        'instructor_id': instructor_id,
                        'day': day_name,
                        'section_id': entry['section_id'],
                        'time': entry['time_slot_str']
                    })
        return output

    def get_class_availability(self):
        class_schedule = defaultdict(lambda: defaultdict(list))
        for idx, gene in enumerate(self.genes):
            day, timeslot_idx, room = gene
            section = self.sections[idx]

            start_time = self.convert_minutes_to_time(self.timeslots[timeslot_idx])
            end_time = self.convert_minutes_to_time((self.timeslots[timeslot_idx] + section['duration']))
            time_slot_str = f"{start_time} - {end_time}"
            class_slot = {'section_id': section['id'], 'time_slot_str': time_slot_str}
            class_schedule[room][day].append(class_slot)

        output = []
        for classroom_id, schedule in class_schedule.items():
            for day, entries in schedule.items():
                day_name = self.get_day_name(day)
                for entry in entries:
                    output.append({
                        'classroom_id': classroom_id,
                        'day': day_name,
                        'section_id': entry['section_id'],
                        'time': entry['time_slot_str']
                    })
        return output

    def get_student_timetable(self):
        student_schedule = defaultdict(lambda: defaultdict(list))
        for idx, gene in enumerate(self.genes):
            day, timeslot_idx, room = gene
            section = self.sections[idx]

            for intake_id in section['intake_ids']:
                start_time = self.convert_minutes_to_time(self.timeslots[timeslot_idx])
                end_time = self.convert_minutes_to_time((self.timeslots[timeslot_idx] + section['duration']))
                time_slot_str = f"{start_time} - {end_time}"
                student_slot = {'section_id': section['id'], 'classroom_id': room, 'time_slot_str': time_slot_str}
                student_schedule[intake_id][day].append(student_slot)

        output = []
        for intake_id, schedule in student_schedule.items():
            for day, time_slots in schedule.items():
                day_name = self.get_day_name(day)
                for slot in time_slots:
                    output.append({
                        'intake_id': intake_id,
                        'day': day_name,
                        'section_id': slot['section_id'],
                        'classroom_id': slot['classroom_id'],
                        'time': slot['time_slot_str']
                    })
        return output
    
    def get_all_slots(self):
        slots = []
        for idx, gene in enumerate(self.genes):
            day, timeslot_idx, room = map(int, gene)
            section = self.sections[idx]

            for intake_id in section['intake_ids']:
                slot = {
                    'intake_id': int(intake_id),
                    'section_id': int(section['id']),
                    'instructor_id': int(section['instructor_id']),
                    'classroom_id': int(room),
                    'start_time': self.convert_minutes_to_time(int(self.timeslots[timeslot_idx])),
                    'end_time': self.convert_minutes_to_time(int((self.timeslots[timeslot_idx] + section['duration']))),
                    'day': self.get_day_name(day)
                }
                slots.append(slot)
        return slots

def convert_to_native(obj):
    if isinstance(obj, dict):
        return {convert_to_native(k): convert_to_native(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_native(i) for i in obj]
    elif isinstance(obj, np.generic):
        return obj.item()
    else:
        return obj

def ga_preference(request):

    start_times = generate_time_options(8, 30, 10, 30, 15)  # From 8:30 AM to 5:00 PM in 15-minute intervals
    end_times = generate_time_options(16, 00, 18, 0, 15, descending=True)  # From 8:30 AM to 6:00 PM in 15-minute intervals
    max_time_gaps = generate_time_gap_options(60, 120, 15)
    min_time_gaps = generate_time_gap_options(15, 45, 15)
    lunch_duration = generate_time_gap_options(30, 60, 15)
    lunch_times = generate_time_options(12, 0, 13, 0, 15) 
    min_classes_per_day = generate_option_range(1, 2, 1)  # Minimum classes per day from 1 to 6
    
    max_generations = generate_option_range(1000, 10000, 100)  # Maximum generations for the GA from 50 to 500
    population_size = generate_option_range(100, 1000, 100)  # Population size for the GA from 10 to 100

    if request.method == 'POST':
        try:
            # Process the form data
            preferences = {
                'start_time': int(request.POST.get('start_time', request.session['ga_preferences'].get('start_time'))),
                'end_time': int(request.POST.get('end_time', request.session['ga_preferences'].get('end_time'))),
                'min_time_gap': int(request.POST.get('min_time_gap', request.session['ga_preferences'].get('min_time_gap'))),
                'max_time_gap': int(request.POST.get('max_time_gap', request.session['ga_preferences'].get('max_time_gap'))),
                'lunch_start': int(request.POST.get('lunch_start', request.session['ga_preferences'].get('lunch_start'))),
                'lunch_duration': int(request.POST.get('lunch_duration', request.session['ga_preferences'].get('lunch_duration'))),
                'delayed_lunch_start': int(request.POST.get('delayed_lunch_start', request.session['ga_preferences'].get('delayed_lunch_start'))),
                'min_classes_per_day': int(request.POST.get('min_classes_per_day', request.session['ga_preferences'].get('min_classes_per_day'))),
                'max_generations': int(request.POST.get('max_generations', request.session['ga_preferences'].get('max_generations'))),
                'population_size': int(request.POST.get('population_size', request.session['ga_preferences'].get('population_size')))
            }

            # Save preferences in the session or database as needed
            request.session['ga_preferences'] = preferences

            return JsonResponse({'success': True, 'message': 'Preferences have been successfully saved!'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'})

    ensure_default_preferences(request.session)
    
    preferences = request.session.get('ga_preferences', {})

    return render(request, 'timetable/preference.html', {
        'start_times': start_times,
        'end_times': end_times,
        'max_time_gaps': max_time_gaps,
        'min_time_gaps': min_time_gaps,
        'lunch_duration': lunch_duration,
        'lunch_times': lunch_times,
        'min_classes_per_day': min_classes_per_day,
        'max_generations': max_generations,
        'population_size': population_size,
        'preferences': preferences,
    })

def generate_option_range(start, end, step):
    return list(range(start, end + 1, step))


def generate_time_options(start_hour, start_minute, end_hour, end_minute, interval, descending=False):
    times = []
    minutes = start_hour * 60 + start_minute
    end_time = end_hour * 60 + end_minute
    while minutes <= end_time:
        hours, mins = divmod(minutes, 60)
        times.append((minutes, f"{hours:02}:{mins:02}"))
        minutes += interval
    if descending:
        times.sort(reverse=True)
    return times

def generate_time_gap_options(min_gap, max_gap, interval):
    options = []
    for gap in range(min_gap, max_gap + interval, interval):
        hours, minutes = divmod(gap, 60)
        label = f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
        options.append((gap, label.strip()))
    return options

def ensure_default_preferences(session):
    default_preferences = {
        'start_time': 510,  # 8:30 AM
        'end_time': 960,  # 4:00 PM
        'min_time_gap': 15,  # 15 minutes
        'max_time_gap': 60,  # 1 hour
        'lunch_start': 720,  # 12:00 PM
        'lunch_duration': 60,
        'delayed_lunch_start': 30,
        'min_classes_per_day': 1,
        'max_generations': 1000,
        'population_size': 100,
    }
    if 'ga_preferences' not in session:
        session['ga_preferences'] = default_preferences


class CustomLoginView(LoginView):
    template_name = 'registration/login.html'

    def get_success_url(self):
        user = self.request.user
        if user.groups.filter(name='Students').exists():
            return reverse('student_dashboard')  # Redirect to student dashboard
        else:
            return reverse('index')