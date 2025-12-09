"""
Конфигурация WSGI для проекта calendar_project.

 Она предоставляет вызываемый объект WSGI в виде переменной уровня модуля с
 именем ``application``.

 Дополнительную информацию об этом файле см. на странице
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Устанавливаем переменную окружения DJANGO_SETTINGS_MODULE.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'calendar_project.settings')

# Создаем WSGI приложение.
application = get_wsgi_application()
