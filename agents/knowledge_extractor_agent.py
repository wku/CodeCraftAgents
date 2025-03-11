import json
from typing import Dict, Any
from utils import call_openrouter, add_to_qdrant, logger
from .base_agent import BaseAgent

class KnowledgeExtractorAgent(BaseAgent):
    def run(self, data: Any) -> Dict[str, Any]:
        data_str = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
        prompt = f"""
        Ты — Агент-экстрактор знаний. Извлеки данные из: {data_str[:1000]}{"..." if len(data_str) > 1000 else ""}. Тебе нужно:
        1. Выделить ключевые элементы (интерфейсы, логика, зависимости).
        2. Верни [{{"category": "", "data": ""}}] в JSON без обёрток.
        Категории знаний:
        - logic: описание логики и алгоритмов
        - interface: описание интерфейсов (входы/выходы)
        - dependency: внешние зависимости
        - pattern: паттерны проектирования
        - error: обнаруженные ошибки или проблемы
        """
        logger.info(f"Промпт для KnowledgeExtractorAgent: {prompt}")
        try:
            result = call_openrouter(prompt)
            result = self._clean_json_response(result)
            result_json = json.loads(result)
            for i, entry in enumerate(result_json):
                add_to_qdrant(entry["category"], entry["data"], point_id=i + len(result_json) * 1000)
            verification = self.verifier.verify("knowledge", result_json, "")
            confidence = verification["confidence"] if verification["status"] == "passed" else self._estimate_confidence(result_json, verification["issues"])
            return self._format_result(result_json, confidence, "knowledge")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка JSON в KnowledgeExtractorAgent: {result}, {str(e)}")
            return self._format_result({"error": "Invalid JSON", "raw": result}, 0.0, "knowledge")
        except Exception as e:
            logger.error(f"Непредвиденная ошибка в KnowledgeExtractorAgent: {str(e)}")
            return self._format_result({"error": str(e)}, 0.0, "knowledge")