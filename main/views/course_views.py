from django.contrib import messages
from django.forms import formset_factory, inlineformset_factory
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from ..models import Course, Section
from django.utils import timezone
from ..forms import CourseForm, SectionForm

def index(request):
    courses = Course.objects.all().prefetch_related('sections')

    return render(request, 'course/index.html', {'courses': courses, 'local_timezone': timezone.get_current_timezone()})

def create(request):
    SectionFormSet = inlineformset_factory(Course, Section, form=SectionForm, extra=1)
    
    if request.method == 'POST':
        course_form = CourseForm(request.POST)
        section_formset = SectionFormSet(request.POST)

        if course_form.is_valid() and section_formset.is_valid():
            course = course_form.save()
            section_formset.instance = course
            section_formset.save()

            return JsonResponse({'success': True, 'message': 'Course has been successfully created!'})
        
        else:
            errors = {}

            course_errors = course_form.errors.get_json_data()
            for field, error_list in course_errors.items():
                errors[field] = [error['message'] for error in error_list] 

            formset_errors = {}
            for form_idx, form in enumerate(section_formset.forms):
                for field, error_list in form.errors.items():
                    # Adjust the key to match the input names in the HTML
                    new_key = f'sections-{form_idx}-{field}'
                    formset_errors[new_key] = error_list

            errors.update(formset_errors)
            
            return JsonResponse({'success': False, 'errors': errors})

    else:
        course_form = CourseForm()
        section_formset = SectionFormSet()

    return render(request, 'course/create.html', {'course_form': course_form, 'section_formset': section_formset})

def edit(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    num_existing_sections = course.sections.count()
    extra_forms = 1 if num_existing_sections == 0 else 0
    SectionFormSet = inlineformset_factory(Course, Section, form=SectionForm, extra=extra_forms, can_delete=True)
    # print(request.POST)
    if request.method == 'POST':
        course_form = CourseForm(request.POST, instance=course)
        section_formset = SectionFormSet(request.POST, instance=course)

        if course_form.is_valid() and section_formset.is_valid():
            course_form.save()
            section_formset.save()

            return JsonResponse({'success': True, 'message': 'Course has been successfully updated!'})

        else:
            errors = {}

            course_errors = course_form.errors.get_json_data()
            for field, error_list in course_errors.items():
                errors[field] = [error['message'] for error in error_list] 

            formset_errors = {}
            for form_idx, form in enumerate(section_formset.forms):
                for field, error_list in form.errors.items():
                    print(field, form_idx, num_existing_sections)
                    if field == '__all__':
                        new_key = f'sections-{form_idx}-section_code'
                    else:
                        new_key = f'sections-{form_idx}-{field}'
                    
                    formset_errors[new_key] = error_list

                errors.update(formset_errors)

            return JsonResponse({'success': False, 'errors': errors})

    else:
        course_form = CourseForm(instance=course)
        section_formset = SectionFormSet(instance=course)

    return render(request, 'course/edit.html', {'course_form': course_form, 'section_formset': section_formset})

def delete(request, course_id):
    try:
        course = get_object_or_404(Course, id=course_id)
    except Course.DoesNotExist:
        return JsonResponse(status=404)

    if request.method == 'POST':
        course.delete()

        return JsonResponse({'success': True, 'message': 'Intake has been successfully deleted!'})

    return JsonResponse(status=405)