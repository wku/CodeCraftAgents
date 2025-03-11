FROM python:3.9

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл приложения в контейнер
COPY project/app.py .

# Устанавливаем зависимости
RUN pip install Flask

# Экспонируем порт для Flask
EXPOSE 5000

# Команда для запуска приложения
CMD ["python", "app.py"]