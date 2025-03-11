import json
from typing import Dict, Any
from utils import call_openrouter, save_json, logger
from .base_agent import BaseAgent

class ValidatorAgent(BaseAgent):
    def run(self, plan: Any) -> Dict[str, Any]:
        result = None
        plan_str = json.dumps(plan) if isinstance(plan, dict) else str(plan)
        prompt = f"""
        Ты — Агент-проверяющий. Проверь план: {plan_str}. Тебе нужно:
        1. Проверить входные/выходные данные, логику, зависимости.
        2. Верни {{"status": "approved"}} или {{"status": "rejected", "comments": []}} в JSON без обёрток.
        Критерии проверки:
        - Все поля заполнены и содержат осмысленные значения
        - Входные и выходные данные соответствуют логике
        - Логика соответствует назначению модуля
        - Указаны все необходимые внешние зависимости
        """
        logger.info(f"Промпт для ValidatorAgent: {prompt}")
        try:
            result = call_openrouter(prompt)
            result = self._clean_json_response(result)
            validation = json.loads(result)
            save_json(validation, "project/validation.json")
            verification = self.verifier.verify("validator", validation, "")
            confidence = verification["confidence"] if verification["status"] == "passed" else self._estimate_confidence(validation, verification["issues"])
            return self._format_result(validation, confidence, "validator")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка JSON в ValidatorAgent: {result}, {str(e)}")
            return self._format_result({"error": "Invalid JSON", "raw": result}, 0.0, "validator")
        except Exception as e:
            logger.error(f"Непредвиденная ошибка в ValidatorAgent: {str(e)}")
            return self._format_result({"error": str(e)}, 0.0, "validator")