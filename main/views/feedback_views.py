# views.py
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from main.models import Feedback
from collections import Counter, defaultdict
import json

def index(request):
    feedbacks = Feedback.objects.all()

    # Aggregate the feedback data
    data = {
        'start_time_rank': Counter(),
        'end_time_rank': Counter(),
        'max_time_gap_rank': Counter(),
        'min_time_gap_rank': Counter(),
        'lunch_start_rank': Counter(),
        'lunch_duration_rank': Counter(),
        'delayed_lunch_start_rank': Counter(),
        'min_classes_per_day_rank': Counter(),
    }

    for feedback in feedbacks:
        data['start_time_rank'][feedback.start_time_rank] += 1
        data['end_time_rank'][feedback.end_time_rank] += 1
        data['max_time_gap_rank'][feedback.max_time_gap_rank] += 1
        data['min_time_gap_rank'][feedback.min_time_gap_rank] += 1
        data['lunch_start_rank'][feedback.lunch_start_rank] += 1
        data['lunch_duration_rank'][feedback.lunch_duration_rank] += 1
        data['delayed_lunch_start_rank'][feedback.delayed_lunch_start_rank] += 1
        data['min_classes_per_day_rank'][feedback.min_classes_per_day_rank] += 1

    # Convert Counter objects to dictionaries
    data = {k: dict(v) for k, v in data.items()}

    context = {
        'data': json.dumps(data)  # Convert data to JSON string
    }
    
    return render(request, 'feedback/index.html', context)
