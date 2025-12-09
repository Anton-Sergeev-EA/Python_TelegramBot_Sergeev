import logging
import psycopg2
from psycopg2.extras import DictCursor
from contextlib import contextmanager
import os

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.connection_string = os.getenv(
            'DATABASE_URL',
            'postgresql://postgres:postgres@localhost:5432/calendar_bot'
        )
        self._init_database()
    
    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для подключения к БД"""
        conn = psycopg2.connect(self.connection_string)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    @contextmanager
    def get_cursor(self):
        """Контекстный менеджер для курсора"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                yield cursor
    
    def _init_database(self):
        """Инициализация базы данных и создание таблиц"""
        with self.get_cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    event_name VARCHAR(255) NOT NULL,
                    event_date DATE NOT NULL,
                    event_time TIME,
                    event_details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_states (
                    user_id BIGINT PRIMARY KEY,
                    state VARCHAR(50),
                    event_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')


class Calendar:
    def __init__(self, db: Database):
        self.db = db
    
    def create_event(self, user_id, event_name, event_date, event_time=None,
                     event_details=None):
        """Создает новое событие"""
        with self.db.get_cursor() as cursor:
            cursor.execute('''
                INSERT INTO events (user_id, event_name, event_date,
                event_time,  event_details)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            ''', (user_id, event_name, event_date, event_time, event_details))
            result = cursor.fetchone()
            return result['id'] if result else None
    
    def get_user_events(self, user_id):
        """Получает все события пользователя"""
        with self.db.get_cursor() as cursor:
            cursor.execute('''
                SELECT id, event_name, event_date, event_time, event_details
                FROM events
                WHERE user_id = %s
                ORDER BY event_date, event_time
            ''', (user_id,))
            return cursor.fetchall()
    
    def get_event(self, user_id, event_id):
        """Получает конкретное событие пользователя"""
        with self.db.get_cursor() as cursor:
            cursor.execute('''
                SELECT * FROM events
                WHERE user_id = %s AND id = %s
            ''', (user_id, event_id))
            return cursor.fetchone()
    
    def edit_event(self, user_id, event_id, **kwargs):
        """Редактирует событие"""
        if not kwargs:
            return False
        
        set_clauses = []
        params = []
        
        for key, value in kwargs.items():
            if value is not None:
                set_clauses.append(f"{key} = %s")
                params.append(value)
        
        if not set_clauses:
            return False
        
        params.extend([user_id, event_id])
        
        with self.db.get_cursor() as cursor:
            cursor.execute(f'''
                UPDATE events
                SET {', '.join(set_clauses)}
                WHERE user_id = %s AND id = %s
            ''', params)
            return cursor.rowcount > 0
    
    def delete_event(self, user_id, event_id):
        """Удаляет событие"""
        with self.db.get_cursor() as cursor:
            cursor.execute('''
                DELETE FROM events
                WHERE user_id = %s AND id = %s
            ''', (user_id, event_id))
            return cursor.rowcount > 0
        