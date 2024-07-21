from .models import Course
from django.core.serializers.json import DjangoJSONEncoder
import json

def global_context(request):
    courses = Course.objects.all().prefetch_related('sections')
    
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

    context = {
        'courses_json': json.dumps(courses_data, cls=DjangoJSONEncoder),
    }
        
    return context