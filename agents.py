# agents.py
import json
import re
import os
import ast
from typing import Dict, Any, Optional, List, Union
from utils import call_openrouter, save_json, save_text, load_json, add_to_qdrant, get_from_qdrant, logger
from verification import VerificationAgent

from utils import logger, call_openrouter, save_json, save_text, load_json, add_to_qdrant, get_from_qdrant
from request_validation_agent import RequestValidationAgent


class BaseAgent:
    def __init__(self):
        self.verifier = VerificationAgent()

    def _clean_json_response(self, text: str) -> str:
        """Очистка JSON-ответа от маркеров и форматирования."""
        # Удаление маркеров кода
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*$', '', text)
        # Удаление начальных и конечных пробелов
        text = text.strip()
        # Исправление разделителей объектов в массивах JSON
        text = re.sub(r'}(\s*){', '},\\1{', text)
        return text

    def _estimate_confidence(self, result: Any, issues: list = None) -> float:
        """Оценка уверенности агента в своём результате."""
        confidence = 1.0
        if not result:
            confidence -= 0.5
        if issues:  # Проверка, что issues не None и не пустой список
            confidence -= 0.1 * len (issues)
        return max (0.0, min (1.0, confidence))


    def _estimate_confidence_old(self, result: Any, issues: list = []) -> float:
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

        logger.info (f"BaseAgent._format_result: Входные данные - data типа {type (data)}, confidence={confidence}, source={source}")

        # Проверяем, есть ли проблемные case-ы
        if isinstance (data, list):
            logger.warning (f"BaseAgent._format_result: data является списком, а не строкой! Преобразуем в строку.")
            data = "\n".join (str (item) for item in data) if data else ""

        result = {
            "source": source,
            "data": data,
            "confidence": confidence,
            "timestamp": import_time ()
        }

        logger.info (f"BaseAgent._format_result: Возвращаемый результат типа {type (result)}, data внутри типа {type (result['data'])}")
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

def import_time():
    """Импорт модуля time для получения временной метки."""
    import time
    return time.time()

class DecomposerAgent(BaseAgent):
    def run(self, task: str) -> Dict[str, Any]:
        """Разбор задачи на модули и интерфейсы."""
        # Получение контекста из базы знаний
        context = get_from_qdrant(task)
        context_str = json.dumps(context) if context else "Нет доступного контекста"
        
        # Формирование промпта с учетом контекста
        prompt = f"""
        Ты — Агент-декомпозер. Твоя задача — разобрать задачу: "{task}". Контекст: {context_str}. Тебе нужно:
        1. Выделить ключевые элементы: модули, интерфейсы, логику, зависимости.
        2. Сформировать план в JSON: {{"modules": [{{"name": "строка с именем модуля", "input": {{"имя_параметра": "тип"}}, "output": {{"имя_результата": "тип"}}, "logic": "строка с описанием логики", "external": ["список зависимостей"]}}]}}. Убедись, что поле "logic" — это строка, а не список или другой тип.
        3. Весь текст отдавай на русском языке, локализация северная европа.
        4. Верни результат в формате JSON без обёрток.

        Для API-сервера обязательно указать:
        - Маршруты (routes)
        - Параметры запросов
        - Форматы ответов
        - Внешние зависимости (например, Flask)
        """
        logger.info(f"Промпт для DecomposerAgent: {prompt}")
        
        try:
            # Вызов LLM
            result = call_openrouter(prompt)
            
            # Очистка и парсинг JSON
            result = self._clean_json_response(result)
            plan = json.loads(result)

            # Постобработка: исправляем поле logic, если оно не строка
            if "modules" in plan:
                for module in plan["modules"]:
                    if "logic" in module and not isinstance (module["logic"], str):
                        logger.info (f"Постобработка: исправляем поле logic, если оно не строка: 1")
                        if isinstance (module["logic"], list):
                            logger.info (f"Постобработка: исправляем поле logic, если оно не строка: 2")
                            module["logic"] = " ".join (str (item) for item in module["logic"])
                        else:
                            logger.info (f"Постобработка: исправляем поле logic, если оно не строка: 3")
                            module["logic"] = str (module["logic"])


            # Сохранение плана для дальнейшего использования
            save_json(plan, "project/plan.json")
            
            # Верификация результата
            verification = self.verifier.verify("decomposer", plan, task)
            confidence = verification["confidence"] if verification["status"] == "passed" else self._estimate_confidence(plan, verification["issues"])
            
            # Добавление результата в базу знаний
            self._add_to_knowledge_base(plan, task)
            
            return self._format_result(plan, confidence, "decomposer")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка JSON в DecomposerAgent: {result}, {str(e)}")
            # В случае ошибки формируем структурированный ответ об ошибке
            return self._format_result({"error": "Invalid JSON", "raw": result}, 0.0, "decomposer")
        except Exception as e:
            logger.error(f"Непредвиденная ошибка в DecomposerAgent: {str(e)}")
            return self._format_result({"error": str(e)}, 0.0, "decomposer")
            
    def _add_to_knowledge_base(self, plan: Dict[str, Any], task: str) -> None:
        """Добавление результатов декомпозиции в базу знаний."""
        try:
            if "modules" in plan:
                for module in plan["modules"]:
                    # Добавляем логику модуля
                    if "logic" in module:
                        add_to_qdrant("logic", module["logic"], point_id=hash(module["logic"]) % 1000000)
                    
                    # Добавляем интерфейсы
                    if "input" in module and "output" in module:
                        interface = {
                            "name": module.get("name", "unknown"),
                            "input": module["input"],
                            "output": module["output"]
                        }
                        add_to_qdrant("interface", json.dumps(interface), point_id=hash(str(interface)) % 1000000)
                    
                    # Добавляем зависимости
                    if "external" in module:
                        for dep in module["external"]:
                            add_to_qdrant("dependency", dep, point_id=hash(dep) % 1000000)
            
            # Добавляем задачу и план
            add_to_qdrant("task", task, point_id=hash(task) % 1000000)
            add_to_qdrant("plan", json.dumps(plan), point_id=hash(str(plan)) % 1000000)
        except Exception as e:
            logger.error(f"Ошибка при добавлении в базу знаний: {str(e)}")

class ValidatorAgent(BaseAgent):
    def run(self, plan: Any) -> Dict[str, Any]:
        """Проверка плана на полноту и корректность."""
        # Формирование промпта для валидации
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
        
        Если какой-то из критериев не выполнен, укажи это в комментариях.
        """
        logger.info(f"Промпт для ValidatorAgent: {prompt}")
        
        try:
            # Вызов LLM
            result = call_openrouter(prompt)
            
            # Очистка и парсинг JSON
            result = self._clean_json_response(result)
            validation = json.loads(result)
            
            # Сохранение результата
            save_json(validation, "project/validation.json")
            
            # Верификация результата
            verification = self.verifier.verify("validator", validation, "")
            confidence = verification["confidence"] if verification["status"] == "passed" else self._estimate_confidence(validation, verification["issues"])
            
            return self._format_result(validation, confidence, "validator")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка JSON в ValidatorAgent: {result}, {str(e)}")
            return self._format_result({"error": "Invalid JSON", "raw": result}, 0.0, "validator")
        except Exception as e:
            logger.error(f"Непредвиденная ошибка в ValidatorAgent: {str(e)}")
            return self._format_result({"error": str(e)}, 0.0, "validator")

class ConsistencyAgent(BaseAgent):
    def run(self, plan: Any) -> Dict[str, Any]:
        """Проверка согласованности типов данных и логики."""
        # Формирование промпта для проверки согласованности
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
            # Вызов LLM
            result = call_openrouter(prompt)
            
            # Очистка и парсинг JSON
            result = self._clean_json_response(result)
            consistency = json.loads(result)
            
            # Сохранение результата
            save_json(consistency, "project/consistency.json")
            
            # Верификация результата
            verification = self.verifier.verify("consistency", consistency, "", {"decomposer": plan})
            confidence = verification["confidence"] if verification["status"] == "passed" else self._estimate_confidence(consistency, verification["issues"])
            
            return self._format_result(consistency, confidence, "consistency")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка JSON в ConsistencyAgent: {result}, {str(e)}")
            return self._format_result({"error": "Invalid JSON", "raw": result}, 0.0, "consistency")
        except Exception as e:
            logger.error(f"Непредвиденная ошибка в ConsistencyAgent: {str(e)}")
            return self._format_result({"error": str(e)}, 0.0, "consistency")

class CodeGeneratorAgent_old(BaseAgent):
    def run(self, plan: Any) -> Dict[str, Any]:
        """Генерация Python-кода по плану."""
        # Формирование промпта для генерации кода
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
        """
        logger.info(f"Промпт для CodeGeneratorAgent: {prompt}")
        
        try:
            # Вызов LLM
            code = call_openrouter(prompt)
            
            # Очистка кода от маркеров
            code = re.sub(r'```python\s*', '', code)
            code = re.sub(r'```\s*$', '', code).strip()
            
            # Сохранение кода
            save_text(code, "project/app.py")
            
            # Проверка синтаксиса
            syntax_issues = self._validate_python_syntax(code)

            # Логирование перед верификацией
            logger.info (f"CodeGeneratorAgent: Код для верификации, тип: {type (code)}, размер: {len (code)}")
            logger.info (f"CodeGeneratorAgent: Синтаксические проблемы, тип: {type (syntax_issues)}, кол-во: {len (syntax_issues)}")


            # Верификация кода todo
            verification = self.verifier.verify("codegen", code, "", {"decomposer": plan})

            logger.info(f"CodeGeneratorAgent: Результат верификации, тип: {type(verification)}, статус: {verification.get('status', 'unknown')}")


            # Правильно объединяем списки issues todo ?
            issues = verification.get ("issues", [])
            logger.info(f"CodeGeneratorAgent: Issues из верификации, тип: {type(issues)}, кол-во: {len(issues)}")


            if syntax_issues:
                issues.extend (syntax_issues)
                logger.info(f"CodeGeneratorAgent: Объединенные issues, тип: {type(issues)}, кол-во: {len(issues)}")

            # Логирование перед вычислением confidence
            if verification.get ("status") == "passed":
                confidence = verification["confidence"]
                logger.info (f"CodeGeneratorAgent: Confidence напрямую из верификации: {confidence}")
            else:
                logger.info (f"CodeGeneratorAgent: Вызов _estimate_confidence с code типа {type (code)} и issues типа {type (issues)}")
                confidence = self._estimate_confidence (code, issues)
                logger.info (f"CodeGeneratorAgent: Рассчитанный confidence: {confidence}")


            # Логирование перед форматированием результата
            logger.info (f"CodeGeneratorAgent: Вызов _format_result с code типа {type (code)}, confidence={confidence}")
            result = self._format_result (code, confidence, "codegen")
            logger.info (f"CodeGeneratorAgent: Результат _format_result, тип: {type (result)}")

            return result

        except Exception as e:
            logger.error(f"Ошибка в CodeGeneratorAgent: {str(e)}")
            return self._format_result({"error": str(e)}, 0.0, "codegen")


class CodeGeneratorAgent (BaseAgent):
    def run(self, plan: Any) -> Dict[str, Any]:
        """Генерация Python-кода по плану."""
        # Формирование промпта для генерации кода
        plan_str = json.dumps (plan) if isinstance (plan, dict) else str (plan)
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
        - Для подсчета 10 наиболее часто встречающихся слов использовать collections.Counter, а не defaultdict
        """
        logger.info (f"Промпт для CodeGeneratorAgent: {prompt}")

        try:
            # Вызов LLM
            code = call_openrouter (prompt)

            # Очистка кода от маркеров
            code = re.sub (r'```python\s*', '', code)
            code = re.sub (r'```\s*$', '', code).strip ()

            # Сохранение кода
            save_text (code, "project/app.py")

            # Проверка синтаксиса
            syntax_issues = self._validate_python_syntax (code)

            # Логирование перед верификацией
            logger.info (f"CodeGeneratorAgent: Код для верификации, тип: {type (code)}, размер: {len (code)}")
            logger.info (f"CodeGeneratorAgent: Синтаксические проблемы, тип: {type (syntax_issues)}, кол-во: {len (syntax_issues)}")

            # Верификация кода
            verification = self.verifier.verify ("codegen", code, "", {"decomposer": plan})

            logger.info (f"CodeGeneratorAgent: Результат верификации, тип: {type (verification)}, статус: {verification.get ('status', 'unknown')}")

            # Правильно объединяем списки issues
            issues = verification.get ("issues", [])
            logger.info (f"CodeGeneratorAgent: Issues из верификации, тип: {type (issues)}, кол-во: {len (issues)}")

            if syntax_issues:
                issues.extend (syntax_issues)
                logger.info (f"CodeGeneratorAgent: Объединенные issues, тип: {type (issues)}, кол-во: {len (issues)}")

            # Логирование перед вычислением confidence
            if verification.get ("status") == "passed":
                confidence = verification["confidence"]
                logger.info (f"CodeGeneratorAgent: Confidence напрямую из верификации: {confidence}")
            else:
                logger.info (f"CodeGeneratorAgent: Вызов _estimate_confidence с code типа {type (code)} и issues типа {type (issues)}")
                confidence = self._estimate_confidence (code, issues)
                logger.info (f"CodeGeneratorAgent: Рассчитанный confidence: {confidence}")

            # Форматируем результат с явным указанием необходимости выполнения
            result_data = {
                "code": code,
                "file_path": "project/app.py",
                "needs_execution": True  # Указываем, что код нужно выполнить
            }
            logger.info (f"CodeGeneratorAgent: Вызов _format_result с result_data типа {type (result_data)}, confidence={confidence}")
            result = self._format_result (result_data, confidence, "codegen")
            logger.info (f"CodeGeneratorAgent: Результат _format_result, тип: {type (result)}")

            return result

        except Exception as e:
            logger.error (f"Ошибка в CodeGeneratorAgent: {str (e)}")
            return self._format_result ({"error": str (e)}, 0.0, "codegen")





class CodeExtractorAgent(BaseAgent):
    def run(self, code: Any) -> Dict[str, Any]:
        """Извлечение и сохранение кода в файл."""
        # Подготовка кода для обработки
        code_str = None
        if isinstance(code, dict) and "data" in code:
            code_str = code["data"] if isinstance(code["data"], str) else str(code["data"])
        elif isinstance(code, str):
            code_str = code
        else:
            code_str = str(code)
            
        # Формирование промпта для извлечения
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
            # Вызов LLM
            result = call_openrouter(prompt)
            
            # Очистка и парсинг JSON
            result = self._clean_json_response(result)
            result_dict = json.loads(result)
            
            # Получение пути к файлу
            file_path = result_dict.get("file_path", "project/app.py")
            
            # Убедимся, что директория существует
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Сохранение кода в файл
            save_text(code_str, file_path)
            
            # Верификация результата
            verification = self.verifier.verify("extractor", result_dict, "")
            confidence = verification["confidence"] if verification["status"] == "passed" else self._estimate_confidence(result_dict, verification["issues"])
            
            return self._format_result(result_dict, confidence, "extractor")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка JSON в CodeExtractorAgent: {result}, {str(e)}")
            # В случае ошибки используем стандартный путь
            file_path = "project/app.py"
            save_text(code_str, file_path)
            return self._format_result({"file_path": file_path}, 0.5, "extractor")
        except Exception as e:
            logger.error(f"Непредвиденная ошибка в CodeExtractorAgent: {str(e)}")
            return self._format_result({"error": str(e)}, 0.0, "extractor")




class DockerRunnerAgent(BaseAgent):
    def run(self, file_path: str, external: list) -> Dict[str, Any]:
        """Подготовка Docker-файлов."""
        # Проверка типа file_path
        if isinstance(file_path, dict) and "file_path" in file_path:
            file_path = file_path["file_path"]
        
        # Проверка существования файла
        file_exists = os.path.exists(file_path) if isinstance(file_path, str) else False
        
        # Формирование промпта для Docker
        prompt = f"""
Ты — Агент-контейнеризатор. Подготовь Docker для файла: {file_path} с зависимостями: {external}. Тебе нужно:
1. Сгенерировать Dockerfile для Python-приложения.
2. Сгенерировать docker-compose.yml для запуска сервиса.
3. Верни {{"dockerfile": "...", "compose": "..."}} в JSON без обёрток.

Требования:
- Использовать образ Python 3.9 или новее
- Установить все необходимые зависимости ({', '.join(external)})
- Скопировать файл приложения в контейнер
- Экспонировать нужные порты (5000 для Flask)
- В docker-compose настроить пробрасывание портов

Обрати внимание: {"файл существует" if file_exists else "файл будет создан позже"}
"""
        logger.info(f"Промпт для DockerRunnerAgent: {prompt}")
        
        try:
            # Вызов LLM
            result = call_openrouter(prompt)
            
            # Очистка и парсинг JSON
            result = self._clean_json_response(result)
            result_dict = json.loads(result)
            
            # Сохранение Dockerfile и docker-compose.yml
            dockerfile = result_dict.get("dockerfile", "")
            compose = result_dict.get("compose", "")
            
            save_text(dockerfile, "project/Dockerfile")
            save_text(compose, "project/docker-compose.yml")
            
            # Верификация результата
            verification = self.verifier.verify("docker", result_dict, "")
            confidence = verification["confidence"] if verification["status"] == "passed" else self._estimate_confidence(result_dict, verification["issues"])
            
            return self._format_result(result_dict, confidence, "docker")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка JSON в DockerRunnerAgent: {result}, {str(e)}")
            return self._format_result({"error": "Invalid JSON", "raw": result}, 0.0, "docker")
        except Exception as e:
            logger.error(f"Непредвиденная ошибка в DockerRunnerAgent: {str(e)}")
            return self._format_result({"error": str(e)}, 0.0, "docker")

class KnowledgeExtractorAgent(BaseAgent):
    def run(self, data: Any) -> Dict[str, Any]:
        """Извлечение знаний из данных."""
        # Подготовка данных для обработки
        data_str = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
        
        # Формирование промпта для извлечения знаний
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
            # Вызов LLM
            result = call_openrouter(prompt)
            
            # Очистка и парсинг JSON
            result = self._clean_json_response(result)
            result_json = json.loads(result)
            
            # Добавление знаний в базу
            for i, entry in enumerate(result_json):
                add_to_qdrant(entry["category"], entry["data"], point_id=i + len(result_json) * 1000)
            
            # Верификация результата
            verification = self.verifier.verify("knowledge", result_json, "")
            confidence = verification["confidence"] if verification["status"] == "passed" else self._estimate_confidence(result_json, verification["issues"])
            
            return self._format_result(result_json, confidence, "knowledge")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка JSON в KnowledgeExtractorAgent: {result}, {str(e)}")
            return self._format_result({"error": "Invalid JSON", "raw": result}, 0.0, "knowledge")
        except Exception as e:
            logger.error(f"Непредвиденная ошибка в KnowledgeExtractorAgent: {str(e)}")
            return self._format_result({"error": str(e)}, 0.0, "knowledge")

class CoordinatorAgent(BaseAgent):
    def run(self, source: str, data: Any) -> str:
        """Определение следующего агента."""
        # Ожидаемый порядок выполнения
        expected_flow = {
            "decomposer": "validator",
            "validator": "consistency",
            "consistency": "codegen",
            "codegen": "extractor",
            "extractor": "docker",
            "docker": "tester",
            "tester": "docs",
            "docs": None
        }
        
        # Подготовка данных для промпта
        data_str = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
        
        # Формирование промпта для координатора
        prompt = f"""
        Ты — Агент-координатор. Определи следующего агента для данных: {data_str[:500]}{"..." if len(data_str) > 500 else ""} от {source}. 
        
        Порядок: decomposer → validator → consistency → codegen → extractor → docker → tester → docs. 
        
        Обрати внимание на:
        - Статус выполнения предыдущего агента
        - Наличие ошибок в данных
        - Полноту и корректность результатов
        
        Верни только имя следующего агента без дополнительного текста.
        """
        logger.info(f"Промпт для CoordinatorAgent: {prompt}")
        
        # Вызов LLM
        next_agent = call_openrouter(prompt).strip()
        
        # Логика определения следующего агента
        if source in expected_flow:
            # Проверка корректности ответа LLM
            if next_agent not in expected_flow.values():
                logger.warning(f"Координатор предложил {next_agent}, что не является допустимым агентом")
                next_agent = expected_flow[source]
        
        return next_agent

class MonitorAgent(BaseAgent):
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Мониторинг состояния системы и агентов."""
        # Формирование промпта для монитора
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
        
        # Проверка validator_consecutive_runs
        if "validator_consecutive_runs" not in state:
            state["validator_consecutive_runs"] = 0
        
        try:
            # Вызов LLM
            result = call_openrouter(prompt)
            
            # Очистка и парсинг JSON
            result = self._clean_json_response(result)
            monitor_result = json.loads(result)
            
            # Верификация результата
            verification = self.verifier.verify("monitor", monitor_result, "")
            confidence = verification["confidence"] if verification["status"] == "passed" else self._estimate_confidence(monitor_result, verification["issues"])
            
            return self._format_result(monitor_result, confidence, "monitor")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка JSON в MonitorAgent: {result}, {str(e)}")
            return self._format_result({"command": "none"}, 0.5, "monitor")
        except Exception as e:
            logger.error(f"Непредвиденная ошибка в MonitorAgent: {str(e)}")
            return self._format_result({"command": "none", "error": str(e)}, 0.5, "monitor")

class TesterAgent(BaseAgent):
    def run_(self, plan: Any, code: Any = None) -> Dict[str, Any]:
        """Создание тестов для кода."""
        result = None  # Инициализация переменной в начале
        # Загрузка плана и кода
        if code is None:
            code = load_json("project/plan.json") if os.path.exists("project/plan.json") else "No code available"
        
        # Извлечение кода из различных форматов
        code_str = None
        if isinstance(code, dict) and "data" in code:
            code_str = code["data"] if isinstance(code["data"], str) else str(code["data"])
        elif isinstance(code, str):
            code_str = code
        else:
            code_str = str(code)
        
        # Если файл app.py существует, читаем его содержимое
        if os.path.exists("project/app.py"):
            with open("project/app.py", "r") as f:
                code_str = f.read()
        
        # Формирование промпта для тестов
        prompt = f"""
    Ты — Агент-тестировщик. Создай тесты для кода:
    
    {code_str[:1000]}{"..." if len(code_str) > 1000 else ""}
    
    План тестирования:
    1. Тесты должны использовать pytest
    2. Проверить основные функции и маршруты
    3. Включить тесты на граничные случаи и обработку ошибок
    4. Использовать моки для внешних зависимостей
    
    Верни {{"tests": "..."}} в JSON без обёрток.
    """
        logger.info(f"Промпт для TesterAgent: {prompt}")
        
        try:
            # Вызов LLM
            result = call_openrouter(prompt)
            
            # Очистка и парсинг JSON
            result = self._clean_json_response(result)
            result_dict = json.loads(result)
            
            # Сохранение тестов
            save_text(result_dict["tests"], "project/test_app.py")
            
            # Верификация результата
            verification = self.verifier.verify("tester", result_dict, "", {"codegen": code_str})
            confidence = verification["confidence"] if verification["status"] == "passed" else self._estimate_confidence(result_dict, verification["issues"])
            
            return self._format_result(result_dict, confidence, "tester")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка JSON в TesterAgent: {result}, {str(e)}")
            return self._format_result({"error": "Invalid JSON", "raw": result}, 0.0, "tester")
        except Exception as e:
            logger.error(f"Непредвиденная ошибка в TesterAgent: {str(e)}")
            return self._format_result({"error": str(e)}, 0.0, "tester")

    def run(self, plan: Any, code: Any = None) -> Dict[str, Any]:
        """Создание тестов для кода, учитывающих аргументы командной строки."""
        # Загрузка плана и кода
        if code is None:
            code = load_json ("project/plan.json") if os.path.exists ("project/plan.json") else "No code available"

        # Извлечение кода из различных форматов
        code_str = None
        if isinstance (code, dict) and "data" in code:
            code_str = code["data"] if isinstance (code["data"], str) else str (code["data"])
        elif isinstance (code, str):
            code_str = code
        else:
            code_str = str (code)

        # Если файл app.py существует, читаем его содержимое
        if os.path.exists ("project/app.py"):
            with open ("project/app.py", "r") as f:
                code_str = f.read ()

        # Анализ требуемых аргументов для тестов
        from utils import call_openrouter

        prompt_args = f"""
    Проанализируй следующий Python-код и определи:

    1. Какие аргументы командной строки требуются для запуска программы?
    2. Какие типы входных файлов обрабатывает программа?
    3. Какие тесты следует написать для проверки основной функциональности?

    {code_str[:2000]}{"..." if len (code_str) > 2000 else ""}

    Верни JSON следующего формата без дополнительных комментариев:
    {{
      "required_args": [
        {{"name": "имя_аргумента", "value": "тестовое_значение"}}
      ],
      "input_file": {{"required": true/false, "content": "пример содержимого для тестового файла"}},
      "test_cases": [
        {{"description": "описание теста", "args": ["аргументы для этого теста"], "expected_outcome": "ожидаемый результат"}}
      ]
    }}
    """

        try:
            # Анализ кода с помощью LLM
            test_analysis_response = call_openrouter (prompt_args)
            test_analysis_response = re.sub (r'```json|```', '', test_analysis_response).strip ()
            test_analysis = json.loads (test_analysis_response)

            # Формирование промпта для тестов
            prompt = f"""
    Ты — Агент-тестировщик. Создай тесты для кода:

    {code_str[:1000]}{"..." if len (code_str) > 1000 else ""}

    План тестирования (на основе анализа):
    1. Тесты должны использовать pytest
    2. Проверить обработку следующих аргументов командной строки: {json.dumps (test_analysis.get ("required_args", []))}
    3. Создать тестовые файлы для ввода: {json.dumps (test_analysis.get ("input_file", {}))}
    4. Проверить основные функции и результаты по следующим тест-кейсам: {json.dumps (test_analysis.get ("test_cases", []))}
    5. Включить тесты на граничные случаи и обработку ошибок
    6. Использовать моки при необходимости

    Верни {{"tests": "..."}} в JSON без обёрток.
    """
            logger.info (f"Промпт для TesterAgent: {prompt}")

            # Вызов LLM
            result = call_openrouter (prompt)

            # Очистка и парсинг JSON
            result = self._clean_json_response (result)
            result_dict = json.loads (result)

            # Сохранение тестов
            save_text (result_dict["tests"], "project/test_app.py")

            # Верификация результата
            verification = self.verifier.verify ("tester", result_dict, "", {"codegen": code_str})
            confidence = verification["confidence"] if verification[
                                                           "status"] == "passed" else self._estimate_confidence (
                result_dict, verification["issues"])

            return self._format_result (result_dict, confidence, "tester")
        except json.JSONDecodeError as e:
            logger.error (f"Ошибка JSON в TesterAgent: {result}, {str (e)}")
            return self._format_result ({"error": "Invalid JSON", "raw": result}, 0.0, "tester")
        except Exception as e:
            logger.error (f"Непредвиденная ошибка в TesterAgent: {str (e)}")
            return self._format_result ({"error": str (e)}, 0.0, "tester")






class DocumentationAgent(BaseAgent):
    def run(self, plan: Any, code: Any = None) -> Dict[str, Any]:
        """Создание документации для проекта."""
        # Загрузка плана и кода
        plan_str = json.dumps(plan) if isinstance(plan, (dict, list)) else str(plan)
        
        # Проверка наличия кода
        if code is None:
            if os.path.exists("project/app.py"):
                with open("project/app.py", "r") as f:
                    code = f.read()
            else:
                code = "No code available"
        
        # Извлечение кода из различных форматов
        code_str = None
        if isinstance(code, dict) and "data" in code:
            code_str = code["data"] if isinstance(code["data"], str) else str(code["data"])
        elif isinstance(code, str):
            code_str = code
# Формирование промпта для документации
        prompt = f"""
Ты — Агент-документатор. Создай документацию для плана: {plan_str[:500]}{"..." if len(plan_str) > 500 else ""} и кода: {code_str[:1000]}{"..." if len(code_str) > 1000 else ""}. Тебе нужно:
1. Описать интерфейсы (входные/выходные данные) и инструкции по использованию.
2. Подробно описать все конечные точки API и их параметры.
3. Предоставить примеры запросов и ответов.
4. Добавить инструкции по установке и запуску.
5. Верни текст README.md без обёрток.

Документация должна содержать следующие разделы:
- Описание
- Установка
- Использование
- API
- Примеры
- Требования
"""
        logger.info(f"Промпт для DocumentationAgent: {prompt}")
        
        try:
            # Вызов LLM
            docs = call_openrouter(prompt)
            
            # Очистка текста от маркеров
            docs = re.sub(r'```markdown\s*', '', docs)
            docs = re.sub(r'```\s*$', '', docs).strip()
            
            # Сохранение документации
            save_text(docs, "project/README.md")
            
            # Верификация результата
            verification = self.verifier.verify("docs", docs, "", {"decomposer": plan})
            confidence = verification["confidence"] if verification["status"] == "passed" else self._estimate_confidence(docs, verification["issues"])
            
            return self._format_result(docs, confidence, "docs")
        except Exception as e:
            logger.error(f"Ошибка в DocumentationAgent: {str(e)}")
            return self._format_result({"error": str(e)}, 0.0, "docs")

def initialize_agents():
    """Инициализация всех агентов системы."""
    try:
        agents = {
            "request_validation": RequestValidationAgent (),
            "decomposer": DecomposerAgent(),
            "validator": ValidatorAgent(),
            "consistency": ConsistencyAgent(),
            "codegen": CodeGeneratorAgent(),
            "extractor": CodeExtractorAgent(),
            "docker": DockerRunnerAgent(),
            "knowledge": KnowledgeExtractorAgent(),
            "coordinator": CoordinatorAgent(),
            "monitor": MonitorAgent(),
            "tester": TesterAgent(),
            "docs": DocumentationAgent()
        }
        logger.info(f"Инициализировано {len(agents)} агентов: {', '.join(agents.keys())}")
        return agents
    except Exception as e:
        logger.error(f"Ошибка при инициализации агентов: {str(e)}")
        # В случае ошибки возвращаем пустой словарь с базовыми агентами
        return {
            "decomposer": DecomposerAgent(),
            "validator": ValidatorAgent(),
            "consistency": ConsistencyAgent(),
            "codegen": CodeGeneratorAgent(),
            "extractor": CodeExtractorAgent(),
            "docker": DockerRunnerAgent()
        }

if __name__ == "__main__":
    # Пример использования
    agents = initialize_agents()
    task = "Создать API-сервер, роут /sum, возвращает сумму a и b"
    
    # Тестирование агента декомпозиции
    logger.info("Тестирование агента декомпозиции")
    result = agents["decomposer"].run(task)
    print(json.dumps(result, indent=2))
    
    # Сохранение результата для использования другими агентами
    if "data" in result and result["data"]:
        save_json(result["data"], "project/test_plan.json")
        
        # Тестирование агента валидации
        logger.info("Тестирование агента валидации")
        validation_result = agents["validator"].run(result["data"])
        print(json.dumps(validation_result, indent=2))


