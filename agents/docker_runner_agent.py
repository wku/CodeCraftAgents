import json
import os
from typing import Dict, Any
from utils import call_openrouter, save_text, logger
from .base_agent import BaseAgent

class DockerRunnerAgent(BaseAgent):
    def run(self, file_path: str, external: list) -> Dict[str, Any]:
        if isinstance(file_path, dict) and "file_path" in file_path:
            file_path = file_path["file_path"]
        file_exists = os.path.exists(file_path) if isinstance(file_path, str) else False
        prompt = f"""
        Ты — Агент-контейнеризатор. Подготовь Docker для файла: {file_path} с зависимостями: {external}. Тебе нужно:
        1. Сгенерировать Dockerfile для Python-приложения.
        2. Сгенерировать docker-compose.yml для запуска сервиса.
        3. Верни {{"dockerfile": "...", "compose": "..."}} в JSON без обёрток.
        Требования:
        - Использовать образ Python 3.9 или новее
        - Установить все необходимые зависимости ({', '.join(external)})
        - Скопировать файл приложения в контейнер
        - Экспонировать нужные порты (5000 для Flask)
        - В docker-compose настроить пробрасывание портов
        Обрати внимание: {"файл существует" if file_exists else "файл будет создан позже"}
        """
        logger.info(f"Промпт для DockerRunnerAgent: {prompt}")
        try:
            result = call_openrouter(prompt)
            result = self._clean_json_response(result)
            result_dict = json.loads(result)
            save_text(result_dict.get("dockerfile", ""), "project/Dockerfile")
            save_text(result_dict.get("compose", ""), "project/docker-compose.yml")
            verification = self.verifier.verify("docker", result_dict, "")
            confidence = verification["confidence"] if verification["status"] == "passed" else self._estimate_confidence(result_dict, verification["issues"])
            return self._format_result(result_dict, confidence, "docker")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка JSON в DockerRunnerAgent: {result}, {str(e)}")
            return self._format_result({"error": "Invalid JSON", "raw": result}, 0.0, "docker")
        except Exception as e:
            logger.error(f"Непредвиденная ошибка в DockerRunnerAgent: {str(e)}")
            return self._format_result({"error": str(e)}, 0.0, "docker")