from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from main.models import Timetable, TimetableEntry, Intake, Section, Instructor, Classroom
from main.forms import TimetableForm

def edit(request, timetable_id):
    timetable = get_object_or_404(Timetable, id=timetable_id)

    timetable_entries = TimetableEntry.objects.filter(timetable=timetable)

    # Process and group the data
    grouped_student_timetable = {}
    grouped_instructor_schedule = {}
    grouped_class_availability = {}

    if request.method == "POST":
        timetable_form = TimetableForm(request.POST, instance=timetable)

        if timetable_form.is_valid():
            timetable_form.save()

            return JsonResponse({'success': True, 'message': 'Profile has been successfully updated!'})
        else:
            errors = timetable_form.errors
            return JsonResponse({'success': False, 'errors': errors})
        
    def sort_entries(entries):
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        entries.sort(key=lambda x: (day_order.index(x['day']), x['time'].split(' - ')[0]))
        return entries

    for entry in timetable_entries:
        intake = Intake.objects.get(id=entry.intake_id)
        section = Section.objects.get(id=entry.section_id)
        instructor = Instructor.objects.get(id=entry.instructor_id)
        classroom = Classroom.objects.get(id=entry.classroom_id)

        entry_dict = {
            'day': entry.day,
            'section_code': section.section_code,
            'classroom_name': classroom.room,
            'time': f"{entry.start_time.strftime('%H:%M')} - {entry.end_time.strftime('%H:%M')}",
        }

        # Group by intake code
        intake_code = intake.intake_code
        if intake_code not in grouped_student_timetable:
            grouped_student_timetable[intake_code] = []
        grouped_student_timetable[intake_code].append(entry_dict)

        # Group by instructor name
        instructor_name = instructor.instructor_name
        if instructor_name not in grouped_instructor_schedule:
            grouped_instructor_schedule[instructor_name] = []
        grouped_instructor_schedule[instructor_name].append(entry_dict)

        # Group by classroom name
        classroom_name = classroom.room
        if classroom_name not in grouped_class_availability:
            grouped_class_availability[classroom_name] = []
        grouped_class_availability[classroom_name].append(entry_dict)

    grouped_student_timetable = {k: sort_entries(v) for k, v in grouped_student_timetable.items()}
    grouped_instructor_schedule = {k: sort_entries(v) for k, v in grouped_instructor_schedule.items()}
    grouped_class_availability = {k: sort_entries(v) for k, v in grouped_class_availability.items()}

    timetable_form = TimetableForm(instance=timetable)

    context = {
        'timetable_form': timetable_form,
        'grouped_student_timetable': grouped_student_timetable,
        'grouped_instructor_schedule': grouped_instructor_schedule,
        'grouped_class_availability': grouped_class_availability,
    }

    return render(request, 'timetable/edit.html', context)

def delete(request, timetable_id):
    try:
        timetable = get_object_or_404(Timetable, id=timetable_id)
    except Instructor.DoesNotExist:
        return JsonResponse(status=404)

    if request.method == 'POST':
        timetable.delete()

        return JsonResponse({'success': True, 'message': 'Profile has been successfully deleted!'})

    return JsonResponse(status=405)
