FROM python:3.9

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей (если есть)
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir aiohttp Flask

# Копируем приложение
COPY project/app.py .

# Экспонируем порт для Flask
EXPOSE 5000

# Команда для запуска приложения
CMD ["python", "app.py"]