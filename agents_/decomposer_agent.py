import json
from typing import Dict, Any
from utils import call_openrouter, save_json, logger, get_from_qdrant, add_to_qdrant
from base_agent import BaseAgent

class DecomposerAgent(BaseAgent):
    def run(self, task: str) -> Dict[str, Any]:
        context = get_from_qdrant(task)
        context_str = json.dumps(context) if context else "Нет доступного контекста"
        prompt = f"""
        Ты — Агент-декомпозер. Твоя задача — разобрать задачу: "{task}". Контекст: {context_str}. Тебе нужно:
        1. Выделить ключевые элементы: модули, интерфейсы, логику, зависимости.
        2. Сформировать план в JSON: {{"modules": [{{"name": "строка с именем модуля", "input": {{"имя_параметра": "тип"}}, "output": {{"имя_результата": "тип"}}, "logic": "строка с описанием логики", "external": ["список зависимостей"]}}]}}.
        3. Весь текст отдавай на русском языке, локализация северная европа.
        4. Верни результат в формате JSON без обёрток.
        Для API-сервера обязательно указать: маршруты, параметры запросов, форматы ответов, внешние зависимости.
        """
        logger.info(f"Промпт для DecomposerAgent: {prompt}")
        try:
            result = call_openrouter(prompt)
            result = self._clean_json_response(result)
            plan = json.loads(result)
            if "modules" in plan:
                for module in plan["modules"]:
                    if "logic" in module and not isinstance(module["logic"], str):
                        module["logic"] = " ".join(str(item) for item in module["logic"]) if isinstance(module["logic"], list) else str(module["logic"])
            save_json(plan, "project/plan.json")
            verification = self.verifier.verify("decomposer", plan, task)
            confidence = verification["confidence"] if verification["status"] == "passed" else self._estimate_confidence(plan, verification["issues"])
            self._add_to_knowledge_base(plan, task)
            return self._format_result(plan, confidence, "decomposer")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка JSON в DecomposerAgent: {result}, {str(e)}")
            return self._format_result({"error": "Invalid JSON", "raw": result}, 0.0, "decomposer")
        except Exception as e:
            logger.error(f"Непредвиденная ошибка в DecomposerAgent: {str(e)}")
            return self._format_result({"error": str(e)}, 0.0, "decomposer")

    def _add_to_knowledge_base(self, plan: Dict[str, Any], task: str) -> None:
        try:
            if "modules" in plan:
                for module in plan["modules"]:
                    if "logic" in module:
                        add_to_qdrant("logic", module["logic"], point_id=hash(module["logic"]) % 1000000)
                    if "input" in module and "output" in module:
                        interface = {"name": module.get("name", "unknown"), "input": module["input"], "output": module["output"]}
                        add_to_qdrant("interface", json.dumps(interface), point_id=hash(str(interface)) % 1000000)
                    if "external" in module:
                        for dep in module["external"]:
                            add_to_qdrant("dependency", dep, point_id=hash(dep) % 1000000)
            add_to_qdrant("task", task, point_id=hash(task) % 1000000)
            add_to_qdrant("plan", json.dumps(plan), point_id=hash(str(plan)) % 1000000)
        except Exception as e:
            logger.error(f"Ошибка при добавлении в базу знаний: {str(e)}")