import json
import os
from typing import Dict, Any
from utils import call_openrouter, save_text, logger
from base_agent import BaseAgent

class CodeExtractorAgent(BaseAgent):
    def run(self, code: Any) -> Dict[str, Any]:
        code_str = code["data"] if isinstance(code, dict) and "data" in code else str(code)
        prompt = f"""
        Ты — Агент-извлекатель кода. Сохрани код:
        {code_str[:1000]}{"..." if len(code_str) > 1000 else ""}
        Тебе нужно:
        1. Определить имя файла (например, app.py, main.py, server.py).
        2. Верни {{"file_path": "project/app.py"}} в JSON без обёрток.
        Для API-сервера обычно используется имя файла app.py или server.py.
        """
        logger.info(f"Промпт для CodeExtractorAgent: {prompt}")
        try:
            result = call_openrouter(prompt)
            result = self._clean_json_response(result)
            result_dict = json.loads(result)
            file_path = result_dict.get("file_path", "project/app.py")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            save_text(code_str, file_path)
            verification = self.verifier.verify("extractor", result_dict, "")
            confidence = verification["confidence"] if verification["status"] == "passed" else self._estimate_confidence(result_dict, verification["issues"])
            return self._format_result(result_dict, confidence, "extractor")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка JSON в CodeExtractorAgent: {result}, {str(e)}")
            file_path = "project/app.py"
            save_text(code_str, file_path)
            return self._format_result({"file_path": file_path}, 0.5, "extractor")
        except Exception as e:
            logger.error(f"Непредвиденная ошибка в CodeExtractorAgent: {str(e)}")
            return self._format_result({"error": str(e)}, 0.0, "extractor")