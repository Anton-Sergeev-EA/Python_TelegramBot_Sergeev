import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from .states import UserState, EventData, UserStateManager
from .database import Calendar
import re

logger = logging.getLogger(__name__)

# Паттерны валидации.
DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
TIME_PATTERN = re.compile(r'^\d{2}:\d{2}$')


class CommandHandlers:
    def __init__(self, calendar: Calendar, state_manager: UserStateManager):
        self.calendar = calendar
        self.state_manager = state_manager
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start."""
        user = update.effective_user
        await update.message.reply_text(
            f"Привет, {user.first_name}! Я Антон-бот-календарь.\n\n"
            "Доступные команды:\n"
            "/create_event - создать событие\n"
            "/my_events - показать мои события\n"
            "/edit_event - редактировать событие\n"
            "/delete_event - удалить событие\n"
            "/cancel - отменить текущую операцию\n"
            "/help - помощь"
        )
        self.state_manager.clear_user_state(user.id)
        return ConversationHandler.END
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help."""
        help_text = """
📅 <b>Антон-бот-календарь</b> - управление событиями

<b>Команды:</b>
/create_event - Создать новое событие (пошагово)

/my_events - Показать все мои события

/edit_event - Редактировать событие (пошагово)

/delete_event - Удалить событие (пошагово)

/cancel - Отменить текущую операцию

<b>Примеры даты и времени:</b>
Дата: 2025-12-15 (ГГГГ-ММ-ДД)
Время: 14:30 (ЧЧ:ММ)
        """
        await update.message.reply_text(help_text, parse_mode='HTML')
        return ConversationHandler.END
    
    async def create_event_start(self, update: Update,
                                 context: ContextTypes.DEFAULT_TYPE):
        """Начало создания события."""
        user_id = update.effective_user.id
        self.state_manager.set_user_state(user_id,
                                          UserState.AWAITING_EVENT_NAME,
                                          EventData())
        await update.message.reply_text(
            "Введите название события:"
        )
        return UserState.AWAITING_EVENT_NAME.value
    
    async def handle_event_name(self, update: Update,
                                context: ContextTypes.DEFAULT_TYPE):
        """Обработка названия события."""
        user_id = update.effective_user.id
        event_name = update.message.text.strip()
        
        if not event_name:
            await update.message.reply_text(
                "Название события не может быть пустым. Попробуйте еще раз:")
            return UserState.AWAITING_EVENT_NAME.value
        
        _, event_data = self.state_manager.get_user_state(user_id)
        event_data.name = event_name
        self.state_manager.set_user_state(user_id,
                                          UserState.AWAITING_EVENT_DATE,
                                          event_data)
        
        await update.message.reply_text(
            "Введите дату события в формате ГГГГ-ММ-ДД:\n"
            "Пример: 2025-12-15"
        )
        return UserState.AWAITING_EVENT_DATE.value
    
    async def handle_event_date(self, update: Update,
                                context: ContextTypes.DEFAULT_TYPE):
        """Обработка даты события."""
        user_id = update.effective_user.id
        date_str = update.message.text.strip()
        
        if not DATE_PATTERN.match(date_str):
            await update.message.reply_text(
                "❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД\n"
                "Пример: 2025-12-15\n"
                "Попробуйте еще раз:"
            )
            return UserState.AWAITING_EVENT_DATE.value
        
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            await update.message.reply_text(
                "❌ Несуществующая дата. Проверьте правильность ввода:\n"
                "Попробуйте еще раз:"
            )
            return UserState.AWAITING_EVENT_DATE.value
        
        state, event_data = self.state_manager.get_user_state(user_id)
        event_data.date = date_str
        self.state_manager.set_user_state(user_id,
                                          UserState.AWAITING_EVENT_TIME,
                                          event_data)
        
        await update.message.reply_text(
            "Введите время события в формате ЧЧ:ММ (или отправьте '-' чтобы "
            "пропустить):\n"
            "Пример: 14:30"
        )
        return UserState.AWAITING_EVENT_TIME.value
    
    async def handle_event_time(self, update: Update,
                                context: ContextTypes.DEFAULT_TYPE):
        """Обработка времени события."""
        user_id = update.effective_user.id
        time_str = update.message.text.strip()
        
        if time_str != '-':
            if not TIME_PATTERN.match(time_str):
                await update.message.reply_text(
                    "❌ Неверный формат времени. Используйте ЧЧ:ММ\n"
                    "Пример: 14:30\n"
                    "Попробуйте еще раз (или '-' чтобы пропустить):"
                )
                return UserState.AWAITING_EVENT_TIME.value
            
            try:
                datetime.strptime(time_str, '%H:%M')
            except ValueError:
                await update.message.reply_text(
                    "❌ Неверное время. Проверьте правильность ввода:\n"
                    "Попробуйте еще раз (или '-' чтобы пропустить):"
                )
                return UserState.AWAITING_EVENT_TIME.value
        
        state, event_data = self.state_manager.get_user_state(user_id)
        event_data.time = None if time_str == '-' else time_str
        self.state_manager.set_user_state(user_id,
                                          UserState.AWAITING_EVENT_DETAILS,
                                          event_data)
        
        await update.message.reply_text(
            "Введите описание события (или отправьте '-' чтобы пропустить):"
        )
        return UserState.AWAITING_EVENT_DETAILS.value
    
    async def handle_event_details(self, update: Update,
                                   context: ContextTypes.DEFAULT_TYPE):
        """Обработка описания события и сохранение."""
        user_id = update.effective_user.id
        details = update.message.text.strip()
        
        state, event_data = self.state_manager.get_user_state(user_id)
        event_data.details = None if details == '-' else details
        
        # Сохраняем событие в БД.
        try:
            event_id = self.calendar.create_event(
                user_id=user_id,
                event_name=event_data.name,
                event_date=event_data.date,
                event_time=event_data.time,
                event_details=event_data.details
            )
            
            response_text = (
                f"✅ Событие создано!\n"
                f"🆔 ID: {event_id}\n"
                f"📝 Название: {event_data.name}\n"
                f"📅 Дата: {event_data.date}"
            )
            
            if event_data.time:
                response_text += f"\n⏰ Время: {event_data.time}"
            if event_data.details:
                response_text += f"\n📋 Описание: {event_data.details}"
            
            await update.message.reply_text(response_text)
        
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при создании события. Попробуйте еще раз."
            )
        
        # Очищаем состояние
        self.state_manager.clear_user_state(user_id)
        return ConversationHandler.END
    
    async def my_events(self, update: Update,
                        context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /my_events."""
        user_id = update.effective_user.id
        
        try:
            events = self.calendar.get_user_events(user_id)
            
            if not events:
                await update.message.reply_text("📭 У вас пока нет событий.")
                return ConversationHandler.END
            
            events_text = "📅 <b>Ваши события:</b>\n\n"
            for event in events:
                events_text += (
                    f"🆔 {event['id']}\n"
                    f"📝 {event['event_name']}\n"
                    f"📅 {event['event_date']}"
                )
                if event.get('event_time'):
                    events_text += f" ⏰ {event['event_time']}"
                if event.get('event_details'):
                    events_text += f"\n📋 {event['event_details']}"
                events_text += "\n" + "-" * 30 + "\n"
            
            # Разбиваем сообщение если оно слишком длинное.
            if len(events_text) > 4096:
                for i in range(0, len(events_text), 4096):
                    await update.message.reply_text(
                        events_text[i:i + 4096],
                        parse_mode='HTML'
                    )
            else:
                await update.message.reply_text(events_text, parse_mode='HTML')
        
        except Exception as e:
            logger.error(f"Error getting events: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при получении событий.")
        
        return ConversationHandler.END
    
    async def edit_event_start(self, update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
        """Начало редактирования события."""
        user_id = update.effective_user.id
        self.state_manager.set_user_state(
            user_id,
            UserState.AWAITING_EDIT_EVENT_ID,
            EventData()
        )
        await update.message.reply_text(
            "Введите ID события для редактирования:"
        )
        return UserState.AWAITING_EDIT_EVENT_ID.value
    
    async def handle_edit_event_id(self, update: Update,
                                   context: ContextTypes.DEFAULT_TYPE):
        """Обработка ID события для редактирования."""
        user_id = update.effective_user.id
        event_id_str = update.message.text.strip()
        
        try:
            event_id = int(event_id_str)
        except ValueError:
            await update.message.reply_text(
                "❌ ID должен быть числом. Попробуйте еще раз:"
            )
            return UserState.AWAITING_EDIT_EVENT_ID.value
        
        # Проверяем существование события.
        event = self.calendar.get_event(user_id, event_id)
        if not event:
            await update.message.reply_text(
                "❌ Событие с таким ID не найдено. Попробуйте еще раз:"
            )
            return UserState.AWAITING_EDIT_EVENT_ID.value
        
        state, event_data = self.state_manager.get_user_state(user_id)
        event_data.event_id = event_id
        self.state_manager.set_user_state(user_id,
                                          UserState.AWAITING_EDIT_FIELD,
                                          event_data)
        
        await update.message.reply_text(
            "Что вы хотите изменить?\n"
            "1. Название\n"
            "2. Дату\n"
            "3. Время\n"
            "4. Описание\n\n"
            "Введите номер пункта:"
        )
        return UserState.AWAITING_EDIT_FIELD.value
    
    async def handle_edit_choice(self, update: Update,
                                 context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора поля для редактирования."""
        user_id = update.effective_user.id
        choice = update.message.text.strip()
        
        state, event_data = self.state_manager.get_user_state(user_id)
        
        field_prompts = {
            '1': ('event_name', "Введите новое название события:"),
            '2': ('event_date', "Введите новую дату в формате ГГГГ-ММ-ДД:"),
            '3': ('event_time',
                  "Введите новое время в формате ЧЧ:ММ (или '-' чтобы удалить):"),
            '4': ('event_details',
                  "Введите новое описание (или '-' чтобы удалить):")
        }
        
        if choice not in field_prompts:
            await update.message.reply_text(
                "❌ Неверный выбор. Введите число от 1 до 4:"
            )
            return UserState.AWAITING_EDIT_FIELD.value
        
        field_name, prompt = field_prompts[choice]
        context.user_data['editing_field'] = field_name
        await update.message.reply_text(prompt)
        return UserState.AWAITING_EDIT_VALUE.value
    
    async def handle_edit_value(self, update: Update,
                                context: ContextTypes.DEFAULT_TYPE):
        """Обработка нового значения для поля."""
        user_id = update.effective_user.id
        new_value = update.message.text.strip()
        field = context.user_data.get('editing_field')
        
        state, event_data = self.state_manager.get_user_state(user_id)
        
        # Валидация в зависимости от поля.
        if field == 'event_date':
            if not DATE_PATTERN.match(new_value):
                await update.message.reply_text(
                    "❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД\n"
                    "Попробуйте еще раз:"
                )
                return UserState.AWAITING_EDIT_VALUE.value
            try:
                datetime.strptime(new_value, '%Y-%m-%d')
            except ValueError:
                await update.message.reply_text(
                    "❌ Несуществующая дата. Попробуйте еще раз:"
                )
                return UserState.AWAITING_EDIT_VALUE.value
        
        elif field == 'event_time' and new_value != '-':
            if not TIME_PATTERN.match(new_value):
                await update.message.reply_text(
                    "❌ Неверный формат времени. Используйте ЧЧ:ММ\n"
                    "Попробуйте еще раз (или '-' чтобы удалить время):"
                )
                return UserState.AWAITING_EDIT_VALUE.value
            try:
                datetime.strptime(new_value, '%H:%M')
            except ValueError:
                await update.message.reply_text(
                    "❌ Неверное время. Попробуйте еще раз:"
                )
                return UserState.AWAITING_EDIT_VALUE.value
        
        # Обновляем событие в БД.
        update_data = {
            field: None if new_value == '-' else new_value
        }
        
        try:
            success = self.calendar.edit_event(
                user_id=user_id,
                event_id=event_data.event_id,
                **update_data
            )
            
            if success:
                await update.message.reply_text(
                    f"✅ Событие успешно обновлено!"
                )
            else:
                await update.message.reply_text(
                    "❌ Не удалось обновить событие."
                )
        
        except Exception as e:
            logger.error(f"Error editing event: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при обновлении события."
            )
        
        # Очищаем состояние.
        self.state_manager.clear_user_state(user_id)
        context.user_data.clear()
        return ConversationHandler.END
    
    async def delete_event_start(self, update: Update,
                                 context: ContextTypes.DEFAULT_TYPE):
        """Начало удаления события."""
        user_id = update.effective_user.id
        self.state_manager.set_user_state(
            user_id,
            UserState.AWAITING_DELETE_EVENT_ID,
            EventData()
        )
        await update.message.reply_text(
            "Введите ID события для удаления:"
        )
        return UserState.AWAITING_DELETE_EVENT_ID.value
    
    async def handle_delete_event_id(self, update: Update,
                                     context: ContextTypes.DEFAULT_TYPE):
        """Обработка ID события для удаления."""
        user_id = update.effective_user.id
        event_id_str = update.message.text.strip()
        
        try:
            event_id = int(event_id_str)
        except ValueError:
            await update.message.reply_text(
                "❌ ID должен быть числом. Попробуйте еще раз:"
            )
            return UserState.AWAITING_DELETE_EVENT_ID.value
        
        # Проверяем существование события.
        event = self.calendar.get_event(user_id, event_id)
        if not event:
            await update.message.reply_text(
                "❌ Событие с таким ID не найдено."
            )
            self.state_manager.clear_user_state(user_id)
            return ConversationHandler.END
        
        # Удаляем событие.
        try:
            success = self.calendar.delete_event(user_id, event_id)
            
            if success:
                await update.message.reply_text(
                    f"✅ Событие {event_id} успешно удалено!"
                )
            else:
                await update.message.reply_text(
                    "❌ Не удалось удалить событие."
                )
        
        except Exception as e:
            logger.error(f"Error deleting event: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при удалении события."
            )
        
        # Очищаем состояние.
        self.state_manager.clear_user_state(user_id)
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /cancel."""
        user_id = update.effective_user.id
        self.state_manager.clear_user_state(user_id)
        context.user_data.clear()
        await update.message.reply_text(
            "Текущая операция отменена."
        )
        return ConversationHandler.END
    
    async def handle_message(self, update: Update,
                             context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений (fallback)."""
        await update.message.reply_text(
            "❌ Неизвестная команда. Используйте /help для списка команд."
        )
            