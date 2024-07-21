from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from ..models import Course, Classroom
from ..forms import ClassForm
from django.utils import timezone
from django.http import JsonResponse

def index(request):
    # courses = Course.objects.all().prefetch_related('sections')
    classrooms = Classroom.objects.all()

    return render(request, 'classroom/index.html', {'classrooms': classrooms, 'local_timezone': timezone.get_current_timezone()})

def create(request):
    if request.method == 'POST':
        classroom_form = ClassForm(request.POST)

        if classroom_form.is_valid():
            classroom_form.save()
            return JsonResponse({'success': True, 'message': 'Classroom has been successfully created!'})
        else: 
            errors = classroom_form.errors
            return JsonResponse({'success': False, 'errors': errors})
        
    else:
        classroom_form = ClassForm()

    context = {
        'classroom_form': classroom_form,
    }

    return render(request, 'classroom/create.html', context)


def edit(request, room_id):
    room = get_object_or_404(Classroom, id=room_id)
    
    if request.method == 'POST':
        classroom_form = ClassForm(request.POST, instance = room)
        if classroom_form.is_valid():
            classroom_form.save()
            return JsonResponse({'success': True, 'message': 'Classroom has been successfully edited!'})
        else: 
            errors = classroom_form.errors
            return JsonResponse({'success': False, 'errors': errors})
        
    else:
        classroom_form = ClassForm(instance=room)
        
    context = {
        'classroom_form': classroom_form,
    }

    return render(request, 'classroom/edit.html', context)
        
def delete(request, room_id):
    try:
        room = get_object_or_404(Classroom, id=room_id)
    except Classroom.DoesNotExist:
        return JsonResponse(status=404)

    if request.method == 'POST':
        room.delete()

        return JsonResponse({'success': True, 'message': 'Classroom has been successfully deleted!'})

    return JsonResponse(status=405)