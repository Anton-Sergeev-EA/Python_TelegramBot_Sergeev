import logging
import os
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from bot.database import Database, Calendar
from bot.states import UserStateManager
from bot.handlers import CommandHandlers

# Загрузка переменных окружения.
load_dotenv()

# Настройка логирования.
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Основная функция запуска бота."""
    
    # Инициализация базы данных.
    db = Database()
    calendar = Calendar(db)
    state_manager = UserStateManager(db)
    handlers = CommandHandlers(calendar, state_manager)
    
    # Создание приложения.
    application = Application.builder().token(os.getenv('BOT_TOKEN')).build()
    
    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("help", handlers.help))
    application.add_handler(CommandHandler("my_events", handlers.my_events))
    application.add_handler(CommandHandler("cancel", handlers.cancel))
    
    # Регистрация обработчиков с пошаговой логикой.
    application.add_handler(
        CommandHandler("create_event", handlers.create_event_start))
    application.add_handler(
        CommandHandler("edit_event", handlers.edit_event_start))
    application.add_handler(
        CommandHandler("delete_event", handlers.delete_event_start))
    
    # Обработчик текстовых сообщений.
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,
                                           handlers.handle_message))
    
    # Запуск бота.
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
    