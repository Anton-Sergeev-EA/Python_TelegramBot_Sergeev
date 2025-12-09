"""
URL-конфигурация для API приложения.
Определяет все эндпоинты REST API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventViewSet

# Создаем роутер DRF (Django REST Framework).
router = DefaultRouter()
# Регистрируем ViewSet для событий.
# Будет автоматически созданы следующие маршруты:
# - /api/events/ (GET список, POST создание)
# - /api/events/{id}/ (GET детали, PUT обновление, PATCH частичное обновление, DELETE удаление)
router.register(r'events', EventViewSet, basename='event')

urlpatterns = [
    # Подключаем все маршруты из роутера.
    path('', include(router.urls)),
]
