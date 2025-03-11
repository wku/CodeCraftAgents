import json
import os
import re
from typing import Dict, Any
from utils import call_openrouter, save_text, load_json, logger
from base_agent import BaseAgent

class TesterAgent(BaseAgent):
    def run(self, plan: Any, code: Any = None) -> Dict[str, Any]:
        if code is None:
            code = load_json("project/plan.json") if os.path.exists("project/plan.json") else "No code available"
        code_str = code["data"] if isinstance(code, dict) and "data" in code else str(code)
        if os.path.exists("project/app.py"):
            with open("project/app.py", "r") as f:
                code_str = f.read()
        prompt_args = f"""
        Проанализируй следующий Python-код и определи:
        1. Какие аргументы командной строки требуются для запуска программы?
        2. Какие типы входных файлов обрабатывает программа?
        3. Какие тесты следует написать для проверки основной функциональности?
        {code_str[:2000]}{"..." if len(code_str) > 2000 else ""}
        Верни JSON:
        {{"required_args": [{{"name": "имя_аргумента", "value": "тестовое_значение"}}], "input_file": {{"required": true/false, "content": "пример содержимого"}}, "test_cases": [{{"description": "описание теста", "args": ["аргументы"], "expected_outcome": "ожидаемый результат"}}]}}
        """
        try:
            test_analysis_response = call_openrouter(prompt_args)
            test_analysis_response = re.sub(r'```json|```', '', test_analysis_response).strip()
            test_analysis = json.loads(test_analysis_response)
            prompt = f"""
            Ты — Агент-тестировщик. Создай тесты для кода:
            {code_str[:1000]}{"..." if len(code_str) > 1000 else ""}
            План тестирования:
            1. Тесты должны использовать pytest
            2. Проверить обработку аргументов: {json.dumps(test_analysis.get("required_args", []))}
            3. Создать тестовые файлы: {json.dumps(test_analysis.get("input_file", {}))}
            4. Проверить тест-кейсы: {json.dumps(test_analysis.get("test_cases", []))}
            5. Включить тесты на граничные случаи и обработку ошибок
            6. Использовать моки при необходимости
            Верни {{"tests": "..."}} в JSON без обёрток.
            """
            logger.info(f"Промпт для TesterAgent: {prompt}")
            result = call_openrouter(prompt)
            result = self._clean_json_response(result)
            result_dict = json.loads(result)
            save_text(result_dict["tests"], "project/test_app.py")
            verification = self.verifier.verify("tester", result_dict, "", {"codegen": code_str})
            confidence = verification["confidence"] if verification["status"] == "passed" else self._estimate_confidence(result_dict, verification["issues"])
            return self._format_result(result_dict, confidence, "tester")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка JSON в TesterAgent: {result}, {str(e)}")
            return self._format_result({"error": "Invalid JSON", "raw": result}, 0.0, "tester")
        except Exception as e:
            logger.error(f"Непредвиденная ошибка в TesterAgent: {str(e)}")
            return self._format_result({"error": str(e)}, 0.0, "tester")