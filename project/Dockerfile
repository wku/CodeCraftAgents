FROM python:3.9

# Устанавливаем зависимости
RUN pip install Flask

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл приложения в контейнер
COPY project/app.py .

# Экспонируем порт для Flask
EXPOSE 5000

# Команда для запуска приложения
CMD ["python", "app.py"]