from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional
import json


class UserState(Enum):
    IDLE = "idle"
    AWAITING_EVENT_NAME = "awaiting_event_name"
    AWAITING_EVENT_DATE = "awaiting_event_date"
    AWAITING_EVENT_TIME = "awaiting_event_time"
    AWAITING_EVENT_DETAILS = "awaiting_event_details"
    AWAITING_EDIT_EVENT_ID = "awaiting_edit_event_id"
    AWAITING_EDIT_FIELD = "awaiting_edit_field"
    AWAITING_DELETE_EVENT_ID = "awaiting_delete_event_id"


@dataclass
class EventData:
    """Временное хранилище данных события"""
    name: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    details: Optional[str] = None
    event_id: Optional[int] = None


class UserStateManager:
    def __init__(self, db):
        self.db = db
    
    def get_user_state(self, user_id):
        """Получает состояние пользователя"""
        with self.db.get_cursor() as cursor:
            cursor.execute('''
                SELECT state, event_data
                FROM user_states
                WHERE user_id = %s
            ''', (user_id,))
            result = cursor.fetchone()
            if result:
                event_data = json.loads(result['event_data']) if result[
                    'event_data'] else {}
                return UserState(result['state']), EventData(**event_data)
            return UserState.IDLE, EventData()
    
    def set_user_state(self, user_id, state: UserState,
                       event_data: EventData = None):
        """Устанавливает состояние пользователя"""
        with self.db.get_cursor() as cursor:
            event_data_json = json.dumps(
                asdict(event_data)) if event_data else None
            cursor.execute('''
                INSERT INTO user_states (user_id, state, event_data, updated_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    state = EXCLUDED.state,
                    event_data = EXCLUDED.event_data,
                    updated_at = CURRENT_TIMESTAMP
            ''', (user_id, state.value, event_data_json))
    
    def clear_user_state(self, user_id):
        """Очищает состояние пользователя"""
        with self.db.get_cursor() as cursor:
            cursor.execute('''
                DELETE FROM user_states
                WHERE user_id = %s
            ''', (user_id,))
            