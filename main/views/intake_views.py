from collections import defaultdict
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from ..models import Course, Intake, Section, StudentProfile
from ..forms import IntakeForm
from django.core.serializers.json import DjangoJSONEncoder
import json
from django.utils import timezone
from django.http import Http404, JsonResponse
from django.db.models import Count, Q

def index(request):
    intakes = Intake.objects.prefetch_related('sections__course').annotate(
            active_student_count=Count('students', filter=Q(students__user__is_active=True))
        )

    for intake in intakes:
        course_dict = defaultdict(list)
        for section in intake.sections.all():
            course_dict[section.course].append(section.section_code)
        intake.course_sections = dict(course_dict)
    
    return render(request, 'intake/index.html', {'intakes': intakes, 'local_timezone': timezone.get_current_timezone()})

def create(request):
    courses = Course.objects.all().order_by('name').prefetch_related('sections')
    students = StudentProfile.objects.all().select_related('user')

    courses_data = []
    for course in courses:
        sections_data = list(course.sections.values('id', 'section_code'))

        course_data = {
            'id': course.id,
            'name': course.name,
            'sections': sections_data
        }
        courses_data.append(course_data)

    if request.method == 'POST':
        intake_form = IntakeForm(request.POST)
 
        if intake_form.is_valid():
            intake_instance = intake_form.save()

            sections = request.POST.getlist('sections')
            student_ids = request.POST.getlist('students')

            if sections:
                # Link sections to the newly created intake instance
                intake_instance.sections.set(sections)  # Assuming 'sections' contains a list of section IDs

            if student_ids:
                for student_id in student_ids:
                    student = StudentProfile.objects.get(id=student_id)
                    student.intake = intake_instance
                    student.save()
            
            return JsonResponse({'success': True, 'message': 'Intake has been successfully created!'})
        else: 
            errors = intake_form.errors
            return JsonResponse({'success': False, 'errors': errors})
    else:
        intake_form = IntakeForm()

    context = {
        'courses_json': json.dumps(courses_data, cls=DjangoJSONEncoder),
        'students': students,
        'intake_form': intake_form,
    }

    return render(request, 'intake/create.html', context)

def edit(request, intake_id):
    try:
        intake = get_object_or_404(Intake, id=intake_id)
    except Http404:
        messages.error(request, 'Intake not found')
        return redirect('intake.index')

    
    students = StudentProfile.objects.all().select_related('user')

    courses = Course.objects.all().order_by('name').prefetch_related('sections')

    courses_data = []
    for course in courses:
        sections_data = list(course.sections.values('id', 'section_code'))

        course_data = {
            'id': course.id,
            'name': course.name,
            'sections': sections_data
        }
        courses_data.append(course_data)

    associated_sections = list(intake.sections.values('id', 'section_code'))
    associated_students = list(intake.students.values('id', 'user__username'))

    if request.method == 'POST':
        intake_form = IntakeForm(request.POST, instance=intake)

        if intake_form.is_valid():
            intake_instance = intake_form.save()

            sections = request.POST.getlist('sections')
            student_ids = request.POST.getlist('students')
            
            intake_instance.sections.set(sections)

            # Clear existing students
            intake_instance.students.clear()

            if student_ids:
                # Add new students
                for student_id in student_ids:
                    student = StudentProfile.objects.get(id=student_id)
                    student.intake = intake_instance
                    student.save()

            return JsonResponse({'success': True, 'message': 'Intake has been successfully updated!'})
        
        else:
            errors = intake_form.errors
            return JsonResponse({'success': False, 'errors': errors})

    else:
        intake_form = IntakeForm(instance=intake)

    context = {
        'courses_json': json.dumps(courses_data, cls=DjangoJSONEncoder),
        'intake_form': intake_form,
        'associated_sections': json.dumps(associated_sections, cls=DjangoJSONEncoder),
        'students': students,
        'associated_students': [student['id'] for student in associated_students],
    }

    return render(request, 'intake/edit.html', context)

def delete(request, intake_id):
    try:
        intake = get_object_or_404(Intake, id=intake_id)
    except Intake.DoesNotExist:
        return JsonResponse(status=404)

    if request.method == 'POST':
        intake.delete() 

        return JsonResponse({'success': True, 'message': 'Intake has been successfully deleted!'})
    
    return JsonResponse(status=405)
