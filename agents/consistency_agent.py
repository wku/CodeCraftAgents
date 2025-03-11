import json
from typing import Dict, Any
from utils import call_openrouter, save_json, logger
from .base_agent import BaseAgent

class ConsistencyAgent(BaseAgent):
    def run(self, plan: Any) -> Dict[str, Any]:
        plan_str = json.dumps(plan) if isinstance(plan, dict) else str(plan)
        prompt = f"""
        Ты — Агент-согласователь. Проверь план: {plan_str}. Тебе нужно:
        1. Проверить согласованность типов данных между модулями.
        2. Проверить согласованность логики между модулями.
        3. Верни {{"status": "approved"}} или {{"status": "rejected", "inconsistencies": []}} в JSON без обёрток.
        Критерии согласованности:
        - Типы выходных данных одного модуля совместимы с типами входных данных связанных модулей
        - Логика модулей не противоречит друг другу
        - Нет конфликтов между зависимостями разных модулей
        """
        logger.info(f"Промпт для ConsistencyAgent: {prompt}")
        try:
            result = call_openrouter(prompt)
            result = self._clean_json_response(result)
            consistency = json.loads(result)
            save_json(consistency, "project/consistency.json")
            verification = self.verifier.verify("consistency", consistency, "", {"decomposer": plan})
            confidence = verification["confidence"] if verification["status"] == "passed" else self._estimate_confidence(consistency, verification["issues"])
            return self._format_result(consistency, confidence, "consistency")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка JSON в ConsistencyAgent: {result}, {str(e)}")
            return self._format_result({"error": "Invalid JSON", "raw": result}, 0.0, "consistency")
        except Exception as e:
            logger.error(f"Непредвиденная ошибка в ConsistencyAgent: {str(e)}")
            return self._format_result({"error": str(e)}, 0.0, "consistency")