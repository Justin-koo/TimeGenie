from django.http import HttpResponseRedirect
from django.urls import reverse

class AdminSiteMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Define a list of paths that should be accessible to students
        self.student_accessible_paths = [
            reverse('student_dashboard'),
        ]
        self.instructor_accessible_paths = [
            reverse('instructor_dashboard'),
        ]

    def __call__(self, request):
        # Determine if the request is async or sync
        if hasattr(self.get_response, 'is_coroutine'):
            return self.__acall__(request)
        else:
            return self.__scall__(request)

    def __scall__(self, request):
        # Check if the path is accessible for students, instructors, or if the user is a staff member or admin
        if not request.path.startswith(reverse('login')) and not any(request.path.startswith(path) for path in self.student_accessible_paths + self.instructor_accessible_paths):
            if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser or request.user.groups.filter(name='Students').exists() or request.user.groups.filter(name='Instructors').exists())):
                return HttpResponseRedirect(reverse('login'))
        response = self.get_response(request)
        return response

    async def __acall__(self, request):
        if not request.path.startswith(reverse('login')) and not any(request.path.startswith(path) for path in self.student_accessible_paths + self.instructor_accessible_paths):
            if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser or request.user.groups.filter(name='Students').exists() or request.user.groups.filter(name='Instructors').exists())):
                return HttpResponseRedirect(reverse('login'))
        response = await self.get_response(request)
        return response

class StudentAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # List of paths that students are allowed to access
        student_allowed_paths = [
            reverse('student_dashboard'),
            reverse('student_feedback'),
            reverse('logout'),
        ]

        # Determine if the current user is a student
        is_student = request.user.groups.filter(name='Students').exists()

        # If the user is a student and the request path is not in the allowed list, redirect or deny access
        if is_student and not any(request.path.startswith(allowed_path) for allowed_path in student_allowed_paths):
            # Optionally, you can redirect to the student dashboard or any other appropriate page
            return HttpResponseRedirect(reverse('student_dashboard'))

        response = self.get_response(request)
        return response

class InstructorAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # List of paths that instructors are allowed to access
        instructor_allowed_paths = [
            reverse('instructor_dashboard'),
            reverse('instructor_feedback'),
            reverse('logout'),
        ]

        # Determine if the current user is an instructor
        is_instructor = request.user.groups.filter(name='Instructors').exists()

        # If the user is an instructor and the request path is not in the allowed list, redirect or deny access
        if is_instructor and not any(request.path.startswith(allowed_path) for allowed_path in instructor_allowed_paths):
            # Optionally, you can redirect to the instructor dashboard or any other appropriate page
            return HttpResponseRedirect(reverse('instructor_dashboard'))

        response = self.get_response(request)
        return response
