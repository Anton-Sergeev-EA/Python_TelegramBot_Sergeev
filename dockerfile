FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей для PostgreSQL.
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements файлов.
COPY requirements.txt .
COPY django_app/requirements.txt django_app_requirements.txt

# Установка зависимостей.
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r django_app_requirements.txt

# Для продакшена можно добавить gunicorn.
# RUN pip install gunicorn==21.2.0

# Копирование кода.
COPY bot/ ./bot/
COPY django_app/ ./django_app/

# Установка PYTHONPATH.
ENV PYTHONPATH=/app:$PYTHONPATH
ENV DJANGO_SETTINGS_MODULE=calendar_project.settings

# Точка входа (можно изменить в docker-compose).
CMD ["python", "django_app/manage.py", "runserver", "0.0.0.0:8000"]
