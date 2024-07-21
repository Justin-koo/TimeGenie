import json
import subprocess
import threading
from django.shortcuts import render
from django.urls import reverse
from main.ga import GeneticAlgorithm
from main.models import Classroom, Intake, Section
from django.contrib import messages
from asgiref.sync import async_to_sync
import cProfile
import pstats
# from channels.layers import get_channel_layer

# Create your views here.
def index(request):
    return render(request, 'index.html')

def run_external_ga():
    result = subprocess.run(['python', r'C:\Users\justi\OneDrive\Dokumen\year3\sem2\FYP2\src\algo\test.py'], capture_output=True, text=True)
    return result.stdout

def run_ga():
    # channel_layer = get_channel_layer()
    intakes = Intake.objects.filter(status=1)
    sections = Section.objects.filter(
        course__status=1,
        intakes__in=intakes,
        instructor__status=1,
    ).distinct()
    classrooms = Classroom.objects.filter(status=1)

    population_size = 100
    gene_length = len(sections)
    mutation_rate = 0.1
    max_generations = 100
    generations = 0

    ga = GeneticAlgorithm(population_size, gene_length, mutation_rate, sections, classrooms)

    best_timetable = None
    while True:
        ga.evolve()
        best_timetable = max(ga.population, key=lambda x: x.fitness)
        ga.best_fitness_history.append(best_timetable.fitness)

        # async_to_sync(channel_layer.group_send)(
        #     "ga_progress",
        #     {
        #         "type": "send_progress",
        #         "message": f"Generation {generations}: Best Fitness = {best_timetable.fitness}, Conflict: {best_timetable.conflict}"
        #     }
        # )

        if best_timetable.fitness >= 70:
            break

        generations += 1

    if best_timetable and best_timetable.fitness >= 70:

        output = run_external_ga()
        result = json.loads(output)
        
        result = {
            'student_timetable': best_timetable.get_student_timetable(),
            'instructor_schedule': best_timetable.get_instructor_schedule(),
            'class_availability': best_timetable.get_class_availability()
        }
    else:
        result = None

    # async_to_sync(channel_layer.group_send)(
    #     "ga_progress",
    #     {
    #         "type": "send_progress",
    #         "message": json.dumps({"result": result, "completed": True})
    #     }
    # )
    
def ga_view(request):
    if request.method == "POST":
        error_occurred = False

        # pass data
        try:
            intakes = Intake.objects.filter(status=1)
            if not intakes.exists():
                messages.error(request, "No active intakes found.")
                error_occurred = True
        except Exception as e:
            messages.error(request, f"Error fetching intakes: {e}")
            error_occurred = True

        try:
            sections = Section.objects.filter(
                course__status=1,
                intakes__in=intakes,
                instructor__status=1
            ).select_related('course', 'instructor').prefetch_related('intakes').distinct()

            if not sections.exists():
                messages.error(request, "No active sections found with active instructors.")
                error_occurred = True
        except Exception as e:
            messages.error(request, f"Error fetching sections: {e}")
            error_occurred = True

        try:
            classrooms = Classroom.objects.filter(status=1)
            if not classrooms.exists():
                messages.error(request, "No active classrooms found.")
                error_occurred = True
        except Exception as e:
            messages.error(request, f"Error fetching classrooms: {e}")
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
                messages.error(request, f"Not enough total classroom time available to accommodate all sections. Available time: {total_classroom_slots} minutes, Required time: {total_section_duration} minutes.")
                error_occurred = True

            # Check if there is at least one classroom with enough capacity for each section
            for section in sections:
                total_students = sum(intake.total_students for intake in section.intakes.filter(status=1))
                if not any(classroom.capacity >= total_students for classroom in classrooms):
                    messages.error(request, f"No classrooms have enough capacity to accommodate section {section.section_code} with {total_students} students.")
                    error_occurred = True
                    break

        if error_occurred:
            return render(request, 'index.html')
        

        # output = run_external_ga()
        # print(output)
        # raise
        # result = json.loads(output)

        # return render(request, 'ga_result.html', {
        #     'student_timetable': result.get('student_timetable', []),
        #     'instructor_schedule': result.get('instructor_schedule', []),
        #     'class_availability': result.get('class_availability', [])
        # })

        # threading.Thread(target=run_ga).start()
        # return render(request, 'ga_progress.html')

        # ga parameter
        population_size = 100
        gene_length = len(sections)
        mutation_rate = 0.1
        generations = 1

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

        ga = GeneticAlgorithm(population_size, gene_length, mutation_rate, sections_data, classrooms_data)

        while True:
            ga.evolve()
            best_timetable = max(ga.population, key=lambda x: x.fitness)
            ga.best_fitness_history.append(best_timetable.fitness)

            print(f"Generation {generations}: Best Fitness = {best_timetable.fitness}")
            print(f'Conflict: {best_timetable.conflict}')

            if best_timetable.fitness >= 70:
                student_timetable = best_timetable.get_student_timetable()
                instructor_schedule = best_timetable.get_instructor_schedule()
                class_availability = best_timetable.get_class_availability()
                return render(request, 'ga_result.html', {
                    'student_timetable': student_timetable,
                    'instructor_schedule': instructor_schedule,
                    'class_availability': class_availability
                })
                break

            generations += 1
