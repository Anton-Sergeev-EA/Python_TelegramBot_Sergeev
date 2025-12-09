from rest_framework import serializers
from .models import Event


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'user_id', 'event_name', 'event_date',
                  'event_time', 'event_details', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def validate_event_date(self, value):
        """Валидация даты события."""
        from datetime import date
        if value < date.today():
            raise serializers.ValidationError(
                "Дата события не может быть в прошлом")
        return value
    