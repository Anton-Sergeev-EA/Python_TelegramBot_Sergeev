"""
Конфигурация ASGI для проекта calendar_project.

Она предоставляет вызываемый объект ASGI в виде переменной уровня модуля с
именем ``application``.

Дополнительную информацию об этом файле см. на странице
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'calendar_project.settings')

application = get_asgi_application()
