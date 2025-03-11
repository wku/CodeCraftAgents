import json
import re
import ast
from typing import Dict, Any, List
from me.PRIORITET.me_github.CodeCraftAgents.utils import logger, save_json, save_text
from me.PRIORITET.me_github.CodeCraftAgents.verification import VerificationAgent


class BaseAgent:
    def __init__(self):

        self.verifier = VerificationAgent()

    def _clean_json_response(self, text: str) -> str:
        """Очистка JSON-ответа от маркеров и форматирования."""
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*$', '', text)
        text = text.strip()
        text = re.sub(r'}(\s*){', '},\\1{', text)
        return text

    def _estimate_confidence(self, result: Any, issues: list = None) -> float:
        """Оценка уверенности агента в своём результате."""
        confidence = 1.0
        if not result:
            confidence -= 0.5
        if issues:
            confidence -= 0.1 * len(issues)
        return max(0.0, min(1.0, confidence))

    def _format_result(self, data: Any, confidence: float = 1.0, source: str = None) -> Dict[str, Any]:
        """Форматирование результата с метаданными."""
        if source is None:
            source = self.__class__.__name__

        logger.info(f"BaseAgent._format_result: Входные данные - data типа {type(data)}, confidence={confidence}, source={source}")

        if isinstance(data, list):
            logger.warning(f"BaseAgent._format_result: data является списком, а не строкой! Преобразуем в строку.")
            data = "\n".join(str(item) for item in data) if data else ""

        result = {
            "source": source,
            "data": data,
            "confidence": confidence,
            "timestamp": self._get_timestamp()
        }

        logger.info(f"BaseAgent._format_result: Возвращаемый результат типа {type(result)}, data внутри типа {type(result['data'])}")
        return result

    def _validate_python_syntax(self, code: str) -> List[str]:
        """Проверка синтаксиса Python-кода."""
        issues = []
        try:
            ast.parse(code)
        except SyntaxError as e:
            issues.append(f"Синтаксическая ошибка: {str(e)}")
        except Exception as e:
            issues.append(f"Ошибка при анализе кода: {str(e)}")
        return issues

    def _get_timestamp(self):
        """Получение временной метки."""
        import time
        return time.time()