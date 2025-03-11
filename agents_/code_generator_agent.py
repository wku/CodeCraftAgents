import json
import re
from typing import Dict, Any
from utils import call_openrouter, save_text, logger
from base_agent import BaseAgent

class CodeGeneratorAgent(BaseAgent):
    def run(self, plan: Any) -> Dict[str, Any]:
        plan_str = json.dumps(plan) if isinstance(plan, dict) else str(plan)
        prompt = f"""
        Ты — Агент-генератор кода. Напиши Python-код для плана: {plan_str}. Тебе нужно:
        1. Реализовать модули с учётом входных/выходных данных и логики.
        2. Включить все необходимые импорты и внешние зависимости.
        3. Обеспечить обработку ошибок и валидацию входных данных.
        4. Верни код как текст без обёрток.
        Требования к коду:
        - Код должен быть хорошо структурирован
        - Включить обработку исключений
        - Реализовать валидацию входных данных
        - Код должен быть готов к запуску
        - Для подсчета 10 наиболее часто встречающихся слов использовать collections.Counter
        """
        logger.info(f"Промпт для CodeGeneratorAgent: {prompt}")
        try:
            code = call_openrouter(prompt)
            code = re.sub(r'```python\s*', '', code)
            code = re.sub(r'```\s*$', '', code).strip()
            save_text(code, "project/app.py")
            syntax_issues = self._validate_python_syntax(code)
            verification = self.verifier.verify("codegen", code, "", {"decomposer": plan})
            issues = verification.get("issues", [])
            if syntax_issues:
                issues.extend(syntax_issues)
            confidence = verification["confidence"] if verification["status"] == "passed" else self._estimate_confidence(code, issues)
            result_data = {"code": code, "file_path": "project/app.py", "needs_execution": True}
            return self._format_result(result_data, confidence, "codegen")
        except Exception as e:
            logger.error(f"Ошибка в CodeGeneratorAgent: {str(e)}")
            return self._format_result({"error": str(e)}, 0.0, "codegen")