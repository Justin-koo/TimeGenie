import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from starlette.staticfiles import StaticFiles
from main.consumers import GAProgressConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'timetable.settings')

django_asgi_app = get_asgi_application()

static_files_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')

application = ProtocolTypeRouter({
    "http": URLRouter([
        path('static/<path:path>', StaticFiles(directory=static_files_path), name='static'),
        path("", django_asgi_app),
    ]),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path('ws/ga_progress/', GAProgressConsumer.as_asgi()),
        ])
    ),
})

