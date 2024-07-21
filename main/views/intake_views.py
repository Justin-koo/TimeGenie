from collections import defaultdict
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from ..models import Course, Intake, Section
from ..forms import IntakeForm
from django.core.serializers.json import DjangoJSONEncoder
import json
from django.utils import timezone
from django.http import JsonResponse

def index(request):
    intakes = Intake.objects.prefetch_related('sections__course').all()

    for intake in intakes:
        course_dict = defaultdict(list)
        for section in intake.sections.all():
            course_dict[section.course].append(section.section_code)
        intake.course_sections = dict(course_dict)
    
    return render(request, 'intake/index.html', {'intakes': intakes, 'local_timezone': timezone.get_current_timezone()})

def create(request):
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


    if request.method == 'POST':
        intake_form = IntakeForm(request.POST)
 
        if intake_form.is_valid():
            intake_instance = intake_form.save(commit=False)

            sections = request.POST.getlist('sections')
            total_students = request.POST.get('total_students')

            if not sections or not int(total_students) > 0:
                intake_instance.status = 0

            intake_instance.save()

            if sections:
                # Link sections to the newly created intake instance
                intake_instance.sections.set(sections)  # Assuming 'sections' contains a list of section IDs
            
            return JsonResponse({'success': True, 'message': 'Intake has been successfully created!'})
        else: 
            errors = intake_form.errors
            return JsonResponse({'success': False, 'errors': errors})
    else:
        intake_form = IntakeForm()

    context = {
        'courses_json': json.dumps(courses_data, cls=DjangoJSONEncoder),
        'intake_form': intake_form,
    }

    return render(request, 'intake/create.html', context)

def edit(request, intake_id):
    intake = get_object_or_404(Intake, id=intake_id)

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

    if request.method == 'POST':
        intake_form = IntakeForm(request.POST, instance=intake)

        if intake_form.is_valid():
            intake_instance = intake_form.save(commit=False)

            sections = request.POST.getlist('sections')
            total_students = request.POST.get('total_students')

            if not sections or not int(total_students) > 0:
                intake_instance.status = 0

            intake_instance.save()
            intake_instance.sections.set(sections)

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
