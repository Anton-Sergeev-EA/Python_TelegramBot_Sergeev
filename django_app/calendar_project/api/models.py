from django.db import models


class Event(models.Model):
    user_id = models.BigIntegerField()
    event_name = models.CharField(max_length=255)
    event_date = models.DateField()
    event_time = models.TimeField(null=True, blank=True)
    event_details = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'events'
        ordering = ['event_date', 'event_time']
    
    def __str__(self):
        return f"{self.event_name} ({self.event_date})"


class UserState(models.Model):
    user_id = models.BigIntegerField(primary_key=True)
    state = models.CharField(max_length=50)
    event_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_states'
    
    def __str__(self):
        return f"User {self.user_id} - {self.state}"
    