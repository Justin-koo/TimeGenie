from collections import defaultdict
from django.http import JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from ..models import Course, Instructor, Section
from django.core.serializers.json import DjangoJSONEncoder
import json
from ..forms import InstructorForm
from django.contrib import messages

def index(request):
    instructors = Instructor.objects.all().prefetch_related('sections')

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

            if not assigned_sections:
                instructor.status = 0
            
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
    instructor = get_object_or_404(Instructor, id=instructor_id)

    courses = Course.objects.all().order_by('name').prefetch_related('sections')
    
    courses_data = []
    for course in courses:
        sections_data = []
        for section in course.sections.all():
            if section.instructor_id == instructor.id or section.instructor_id is None:
                sections_data.append({'id': section.id, 'section_code': section.section_code})

        course_data = {
            'id': course.id,
            'name': course.name,
            'sections': sections_data
        }
        courses_data.append(course_data)

    associated_sections = list(instructor.sections.values('id', 'section_code'))

    if request.method == 'POST':
        instructor_form = InstructorForm(request.POST, instance=instructor)

        if instructor_form.is_valid():
            instructor = instructor_form.save(commit=False)

            assigned_sections = request.POST.getlist('sections')

            if not assigned_sections:
                instructor.status = 0

            instructor.save()

           # Clear existing sections for the instructor
            instructor.sections.clear()

            Section.objects.filter(id__in=assigned_sections).update(instructor=instructor)

            return JsonResponse({'success': True, 'message': 'Instructor has been successfully updated!'})

        else:
            errors = instructor_form.errors
            return JsonResponse({'success': False, 'errors': errors})

    else:
        instructor_form = InstructorForm(instance=instructor)

    context = {
        'courses_json': json.dumps(courses_data, cls=DjangoJSONEncoder),
        'instructor_form': instructor_form,
        'associated_sections': json.dumps(associated_sections, cls=DjangoJSONEncoder),
    }

    return render(request, 'instructor/edit.html', context)

def delete(request, instructor_id):
    try:
        instructor = get_object_or_404(Instructor, id=instructor_id)
    except Instructor.DoesNotExist:
        return JsonResponse(status=404)

    if request.method == 'POST':
        instructor.sections.update(instructor=None)

        instructor.delete()

        return JsonResponse({'success': True, 'message': 'Instructor has been successfully deleted!'})

    return JsonResponse(status=405)