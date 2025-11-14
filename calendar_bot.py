import sqlite3
import logging
import requests
import json
import time
import secrets

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = secrets.BOT_TOKEN
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


class Calendar:
    def __init__(self, db_connection):
        self.conn = db_connection
        self.create_table()
    
    def create_table(self):
        """Создает таблицу событий, если она не существует"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_name TEXT NOT NULL,
                event_date TEXT NOT NULL,
                event_time TEXT,
                event_details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
    
    def create_event(self, user_id, event_name, event_date, event_time=None,
                     event_details=None):
        """Создает новое событие"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO events (user_id, event_name, event_date, event_time, event_details)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, event_name, event_date, event_time, event_details))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_user_events(self, user_id):
        """Получает все события пользователя"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, event_name, event_date, event_time, event_details
            FROM events
            WHERE user_id = ?
            ORDER BY event_date, event_time
        ''', (user_id,))
        return cursor.fetchall()
    
    def get_event(self, user_id, event_id):
        """Получает конкретное событие пользователя"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM events
            WHERE user_id = ? AND id = ?
        ''', (user_id, event_id))
        return cursor.fetchone()
    
    def edit_event(self, user_id, event_id, event_name=None, event_date=None,
                   event_time=None, event_details=None):
        """Редактирует событие"""
        cursor = self.conn.cursor()
        
        current_event = self.get_event(user_id, event_id)
        if not current_event:
            return False
        
        updates = []
        params = []
        
        if event_name:
            updates.append("event_name = ?")
            params.append(event_name)
        if event_date:
            updates.append("event_date = ?")
            params.append(event_date)
        if event_time:
            updates.append("event_time = ?")
            params.append(event_time)
        if event_details:
            updates.append("event_details = ?")
            params.append(event_details)
        
        if not updates:
            return False
        
        params.extend([user_id, event_id])
        
        cursor.execute(f'''
            UPDATE events
            SET {', '.join(updates)}
            WHERE user_id = ? AND id = ?
        ''', params)
        
        self.conn.commit()
        return cursor.rowcount > 0
    
    def delete_event(self, user_id, event_id):
        """Удаляет событие"""
        cursor = self.conn.cursor()
        cursor.execute('''
            DELETE FROM events
            WHERE user_id = ? AND id = ?
        ''', (user_id, event_id))
        self.conn.commit()
        return cursor.rowcount > 0


conn = sqlite3.connect('calendar_bot.db', check_same_thread=False)
calendar = Calendar(conn)


def send_message(chat_id, text):
    """Отправляет сообщение пользователю"""
    url = f"{BASE_URL}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, data=data)
        return response.json()
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return None


def handle_command(message):
    """Обрабатывает команды от пользователя"""
    chat_id = message['chat']['id']
    text = message.get('text', '').strip()
    user_id = message['from']['id']
    first_name = message['from'].get('first_name', 'Пользователь')
    
    if text.startswith('/start'):
        send_message(chat_id,
                     f"Привет, {first_name}! Я Антон-бот-календарь.\n\n"
                     "Доступные команды:\n"
                     "/create_event - создать событие\n"
                     "/my_events - показать мои события\n"
                     "/edit_event - редактировать событие\n"
                     "/delete_event - удалить событие\n"
                     "/help - помощь"
                     )
    
    elif text.startswith('/help'):
        help_text = """
📅 <b>Антон-бот-календарь</b> - управление событиями

<b>Команды:</b>
/create_event - Создать новое событие
Формат: /create_event Название; Дата(ГГГГ-ММ-ДД); Время(ЧЧ:ММ); Описание

/my_events - Показать все мои события

/edit_event - Редактировать событие
Формат: /edit_event ID_события; Новое_название; Новая_дата; Новое_время; Новое_описание

/delete_event - Удалить событие
Формат: /delete_event ID_события

<b>Примеры:</b>
/create_event Встреча с друзьями; 2025-12-15; 14:30; Обсуждение праздников
/create_event День рождения; 2025-12-12
/edit_event 1; Встреча с друзьями; 2025-12-16; 15:00; Перенос встречи
/delete_event 1
        """
        send_message(chat_id, help_text)
    
    elif text.startswith('/create_event'):
        try:
            if not text or len(text.split(';')) < 2:
                send_message(chat_id,
                             "❌ Неправильный формат. Используйте:\n"
                             "/create_event Название; Дата(ГГГГ-ММ-ДД); Время(ЧЧ:ММ); Описание\n\n"
                             "Пример: /create_event Встреча; 2024-01-15; 14:30; Обсуждение проекта"
                             )
                return
            
            parts = [part.strip() for part in text[14:].split(';')]
            event_name = parts[0]
            event_date = parts[1] if len(parts) > 1 else None
            event_time = parts[2] if len(parts) > 2 else None
            event_details = parts[3] if len(parts) > 3 else None
            
            if not event_name or not event_date:
                send_message(chat_id, "❌ Название и дата события обязательны!")
                return
            
            # Создаем событие
            event_id = calendar.create_event(user_id, event_name, event_date,
                                             event_time, event_details)
            
            send_message(chat_id,
                         f"✅ Событие создано!\n"
                         f"ID: {event_id}\n"
                         f"Название: {event_name}\n"
                         f"Дата: {event_date}\n"
                         f"Время: {event_time or 'Не указано'}\n"
                         f"Описание: {event_details or 'Нет описания'}"
                         )
        
        except Exception as e:
            logger.error(f"Error in create_event: {e}")
            send_message(chat_id,
                         "❌ Произошла ошибка при создании события. Проверьте формат данных.")
    
    elif text.startswith('/my_events'):
        try:
            events = calendar.get_user_events(user_id)
            
            if not events:
                send_message(chat_id, "📭 У вас пока нет событий.")
                return
            
            events_text = "📅 <b>Ваши события:</b>\n\n"
            for event in events:
                event_id, event_name, event_date, event_time, event_details = event
                events_text += (
                    f"🆔 {event_id}\n"
                    f"📝 {event_name}\n"
                    f"📅 {event_date}"
                )
                if event_time:
                    events_text += f" ⏰ {event_time}"
                if event_details:
                    events_text += f"\n📋 {event_details}"
                events_text += "\n" + "-" * 30 + "\n"
            
            if len(events_text) > 4096:
                for i in range(0, len(events_text), 4096):
                    send_message(chat_id, events_text[i:i + 4096])
            else:
                send_message(chat_id, events_text)
        
        except Exception as e:
            logger.error(f"Error in my_events: {e}")
            send_message(chat_id, "❌ Произошла ошибка при получении событий.")
    
    elif text.startswith('/edit_event'):
        try:
            if not text or len(text.split(';')) < 2:
                send_message(chat_id,
                             "❌ Неправильный формат. Используйте:\n"
                             "/edit_event ID_события; Новое_название; Новая_дата; Новое_время; Новое_описание\n\n"
                             "Пример: /edit_event 1; Встреча; 2025-12-16; "
                             "15:00; Перенос встречи"
                             )
                return
            
            parts = [part.strip() for part in text[12:].split(';')]
            
            try:
                event_id = int(parts[0])
            except ValueError:
                send_message(chat_id, "❌ ID события должен быть числом!")
                return
            
            event_name = parts[1] if len(parts) > 1 else None
            event_date = parts[2] if len(parts) > 2 else None
            event_time = parts[3] if len(parts) > 3 else None
            event_details = parts[4] if len(parts) > 4 else None
            
            current_event = calendar.get_event(user_id, event_id)
            if not current_event:
                send_message(chat_id, "❌ Событие с таким ID не найдено!")
                return
            
            success = calendar.edit_event(user_id, event_id, event_name,
                                          event_date, event_time,
                                          event_details)
            
            if success:
                send_message(chat_id,
                             f"✅ Событие {event_id} успешно обновлено!")
            else:
                send_message(chat_id, "❌ Не удалось обновить событие.")
        
        except Exception as e:
            logger.error(f"Error in edit_event: {e}")
            send_message(chat_id,
                         "❌ Произошла ошибка при редактировании события.")
    
    elif text.startswith('/delete_event'):
        try:
            parts = text.split()
            if len(parts) < 2:
                send_message(chat_id,
                             "❌ Неправильный формат. Используйте:\n"
                             "/delete_event ID_события\n\n"
                             "Пример: /delete_event 1"
                             )
                return
            
            try:
                event_id = int(parts[1])
            except ValueError:
                send_message(chat_id, "❌ ID события должен быть числом!")
                return
            
            current_event = calendar.get_event(user_id, event_id)
            if not current_event:
                send_message(chat_id, "❌ Событие с таким ID не найдено!")
                return
            
            success = calendar.delete_event(user_id, event_id)
            
            if success:
                send_message(chat_id, f"✅ Событие {event_id} успешно удалено!")
            else:
                send_message(chat_id, "❌ Не удалось удалить событие.")
        
        except Exception as e:
            logger.error(f"Error in delete_event: {e}")
            send_message(chat_id, "❌ Произошла ошибка при удалении события.")
    
    else:
        send_message(chat_id,
                     "❌ Неизвестная команда. Используйте /help для списка команд.")


def get_updates(offset=None):
    """Получает обновления от Telegram API"""
    url = f"{BASE_URL}/getUpdates"
    params = {'timeout': 100, 'offset': offset}
    try:
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        logger.error(f"Error getting updates: {e}")
        return None


def main():
    """Основная функция бота"""
    print("Бот запущен и работает...")
    last_update_id = None
    
    while True:
        try:
            updates = get_updates(last_update_id)
            
            if updates and 'result' in updates:
                for update in updates['result']:
                    last_update_id = update['update_id'] + 1
                    
                    if 'message' in update and 'text' in update['message']:
                        handle_command(update['message'])
            
            time.sleep(1)
        
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(5)


if __name__ == '__main__':
    main()