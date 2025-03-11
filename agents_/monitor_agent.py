import json
from typing import Dict, Any
from utils import call_openrouter, logger
from base_agent import BaseAgent

class MonitorAgent(BaseAgent):
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""
        Ты — Агент-монитор. Проверь состояние: {json.dumps(state, indent=2)[:1000]}{"..." if len(json.dumps(state, indent=2)) > 1000 else ""}. Тебе нужно:
        1. Если агент работает >10 минут, верни {{"command": "Перезапустить <имя>"}}.
        2. Если validator >3 раз подряд, верни {{"command": "Принудительный переход к consistency"}}.
        3. Иначе верни {{"command": "none"}} в JSON без обёрток.
        Обрати внимание:
        - Количество последовательных запусков validator: {state.get("validator_consecutive_runs", 0)}
        - Текущий агент: {state.get("current_agent", "unknown")}
        - Текущий шаг: {state.get("step", 0)}
        """
        logger.info(f"Промпт для MonitorAgent: {prompt}")
        if "validator_consecutive_runs" not in state:
            state["validator_consecutive_runs"] = 0
        try:
            result = call_openrouter(prompt)
            result = self._clean_json_response(result)
            monitor_result = json.loads(result)
            verification = self.verifier.verify("monitor", monitor_result, "")
            confidence = verification["confidence"] if verification["status"] == "passed" else self._estimate_confidence(monitor_result, verification["issues"])
            return self._format_result(monitor_result, confidence, "monitor")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка JSON в MonitorAgent: {result}, {str(e)}")
            return self._format_result({"command": "none"}, 0.5, "monitor")
        except Exception as e:
            logger.error(f"Непредвиденная ошибка в MonitorAgent: {str(e)}")
            return self._format_result({"command": "none", "error": str(e)}, 0.5, "monitor")