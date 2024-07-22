from django.contrib import admin
from django.urls import path
from .views import views, course_views, instructor_views, classroom_views, intake_views, timetable_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index, name='index'),
    path('timetable', views.ga_view, name='ga_view'),
    path('timetable/result', views.ga_result, name='ga_result'),
    path('timetable/edit/<int:timetable_id>', timetable_views.edit, name='timetable.edit'),
    path('timetable/delete/<int:timetable_id>', timetable_views.delete, name='timetable.delete'),
    path('check_ga_status', views.check_ga_status, name='check_ga_status'),
    path('course', course_views.index, name='course.index'),
    path('course/create', course_views.create, name='course.create'),
    path('course/edit/<int:course_id>', course_views.edit, name='course.edit'),
    path('course/delete/<int:course_id>', course_views.delete, name='course.delete'),
    path('instructor', instructor_views.index, name='instructor.index'),
    path('instructor/create', instructor_views.create, name='instructor.create'),
    path('instructor/edit/<int:instructor_id>', instructor_views.edit, name='instructor.edit'),
    path('instructor/delete/<int:instructor_id>', instructor_views.delete, name='instructor.delete'),
    path('classroom', classroom_views.index, name='classroom.index'),
    path('classroom/create', classroom_views.create, name='classroom.create'),
    path('classroom/edit/<int:room_id>', classroom_views.edit, name='classroom.edit'),
    path('classroom/delete/<int:room_id>', classroom_views.delete, name='classroom.delete'),
    path('intake', intake_views.index, name='intake.index'),
    path('intake/create', intake_views.create, name='intake.create'),
    path('intake/edit/<int:intake_id>', intake_views.edit, name='intake.edit'),
    path('intake/delete/<int:intake_id>', intake_views.delete, name='intake.delete'),
]+  static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)