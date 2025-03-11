import json
from typing import Dict, Any
from utils import call_openrouter, logger


class RequestValidationAgent:
    def run(self, task: str) -> Dict[str, Any]:
        """
        Проверка входного запроса на соответствие требованиям проекта.

        :param task: Текстовое описание задачи
        :return: Словарь с результатом валидации
        """
        # Формирование промпта для валидации запроса
        prompt = f"""
        Ты - строгий эксперт по техническим заданиям для создания серверных приложений на Python.
        
        Проанализируй следующее техническое задание и определи, соответствует ли оно следующим критериям:
        
        1. Задание предполагает создание серверной или консольной реализации (backend) без frontend
        2. Реализация должна быть в одном Python-файле
        3. Задание не требует создания обязательной многофайловой архитектуры
        4. Задание технически выполнимо в рамках одного питон файла
        
        Техническое задание:
        {task}
        
        Верни JSON-ответ в формате:
        {{
            "is_valid": true/false,
            "reasons": ["список причин", "если задание не валидно"]
        }}
        
        Критически оцени задание. Если есть малейшие сомнения в простоте реализации - верни false.
        """
        try:
            # Вызов LLM для валидации
            result = call_openrouter (prompt)

            # Очистка и парсинг JSON
            result = result.replace ('```json', '').replace ('```', '').strip ()
            validation = json.loads (result)

            # Формирование результата с метаданными
            formatted_result = {
                "source": "request_validation",
                "data": validation,
                "confidence": 0.9 if validation.get ("is_valid", False) else 0.2
            }

            logger.info (f"Валидация запроса: {'Принят' if validation.get ('is_valid', False) else 'Отклонен'}")

            return formatted_result

        except json.JSONDecodeError as e:
            logger.error (f"Ошибка JSON в RequestValidationAgent: {str (e)}")
            return {
                "source": "request_validation",
                "data": {"is_valid": False, "reasons": ["Ошибка парсинга ответа LLM"]},
                "confidence": 0.1
            }
        except Exception as e:
            logger.error (f"Непредвиденная ошибка в RequestValidationAgent: {str (e)}")
            return {
                "source": "request_validation",
                "data": {"is_valid": False, "reasons": [str (e)]},
                "confidence": 0.1
            }

    def __init__(self):
        """Инициализация агента."""
        self.name = "request_validation"