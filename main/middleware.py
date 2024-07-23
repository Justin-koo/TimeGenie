from django.http import HttpResponseRedirect
from django.urls import reverse

class AdminSiteMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Determine if the request is async or sync
        if hasattr(self.get_response, 'is_coroutine'):
            return self.__acall__(request)
        else:
            return self.__scall__(request)

    def __scall__(self, request):
        if not request.path.startswith(reverse('login')):
            if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)):
                return HttpResponseRedirect(reverse('login'))
        response = self.get_response(request)
        return response

    async def __acall__(self, request):
        if not request.path.startswith(reverse('login')):
            if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)):
                return HttpResponseRedirect(reverse('login'))
        response = await self.get_response(request)
        return response
