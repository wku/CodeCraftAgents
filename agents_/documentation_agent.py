import json
import os
import re
from typing import Dict, Any
from utils import call_openrouter, save_text, logger
from base_agent import BaseAgent

class DocumentationAgent(BaseAgent):
    def run(self, plan: Any, code: Any = None) -> Dict[str, Any]:
        plan_str = json.dumps(plan) if isinstance(plan, (dict, list)) else str(plan)
        if code is None and os.path.exists("project/app.py"):
            with open("project/app.py", "r") as f:
                code = f.read()
        code_str = code["data"] if isinstance(code, dict) and "data" in code else str(code)
        prompt = f"""
        Ты — Агент-документатор. Создай документацию для плана: {plan_str[:500]}{"..." if len(plan_str) > 500 else ""} и кода: {code_str[:1000]}{"..." if len(code_str) > 1000 else ""}. Тебе нужно:
        1. Описать интерфейсы и инструкции по использованию.
        2. Подробно описать все конечные точки API и их параметры.
        3. Предоставить примеры запросов и ответов.
        4. Добавить инструкции по установке и запуску.
        5. Верни текст README.md без обёрток.
        Документация должна содержать:
        - Описание
        - Установка
        - Использование
        - API
        - Примеры
        - Требования
        """
        logger.info(f"Промпт для DocumentationAgent: {prompt}")
        try:
            docs = call_openrouter(prompt)
            docs = re.sub(r'```markdown\s*', '', docs)
            docs = re.sub(r'```\s*$', '', docs).strip()
            save_text(docs, "project/README.md")
            verification = self.verifier.verify("docs", docs, "", {"decomposer": plan})
            confidence = verification["confidence"] if verification["status"] == "passed" else self._estimate_confidence(docs, verification["issues"])
            return self._format_result(docs, confidence, "docs")
        except Exception as e:
            logger.error(f"Ошибка в DocumentationAgent: {str(e)}")
            return self._format_result({"error": str(e)}, 0.0, "docs")