from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Event
from .serializers import EventSerializer


class EventViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с событиями через API."""
    serializer_class = EventSerializer
    queryset = Event.objects.all()
    
    def get_queryset(self):
        """Фильтрация событий по user_id."""
        queryset = super().get_queryset()
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        return queryset
    
    @action(detail=False, methods=['get'])
    def user_events(self, request):
        """Получение событий конкретного пользователя."""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        events = Event.objects.filter(user_id=user_id)
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['delete'])
    def delete_by_id(self, request):
        """Удаление события по ID и user_id."""
        user_id = request.query_params.get('user_id')
        event_id = request.query_params.get('event_id')
        
        if not user_id or not event_id:
            return Response(
                {'error': 'user_id and event_id parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        event = get_object_or_404(Event, id=event_id, user_id=user_id)
        event.delete()
        return Response({'message': 'Event deleted successfully'})
    