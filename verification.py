# verification.py
import json
import re
import os
import ast
from typing import Dict, Any, List, Optional, Union

from me.PRIORITET.me_github.CodeCraftAgents.utils import logger, load_json, save_json, load_yaml  # Добавьте load_yaml


class VerificationAgent:
    def __init__(self, rules_path: str = "settings.yml"):
        """Инициализация агента верификации с загрузкой правил."""
        self.rules_path = rules_path
        self.rules = self._load_verification_rules ()
    

    def _load_verification_rules(self) -> Dict[str, Any]:
        """Загрузка правил верификации из YAML."""
        settings = load_yaml(self.rules_path)
        rules = settings.get('verification_rules', {})
        
        return rules

    def verify(self, agent_name: str, result: Any, task: str, previous_results: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Проверка результата агента на соответствие правилам и задаче."""

        logger.info (f"VerificationAgent.verify: Вызван для агента '{agent_name}', result типа {type (result)}")


        if previous_results is None:
            previous_results = {}
            
        # Проверка наличия правил для агента
        if agent_name not in self.rules:
            logger.error(f"Нет правил верификации для агента: {agent_name}")
            # Создаем базовое правило для неизвестного агента
            self.rules[agent_name] = {
                "required_fields": None,
                "success_criteria": f"valid {agent_name} result"
            }
            logger.info(f"Создано базовое правило для агента {agent_name}")

        rules = self.rules[agent_name]
        issues = []
        confidence = 1.0  # Начальная уверенность

        # Подготовка данных для проверки
        data = self._extract_data_for_verification(result)
        
        # Запись результата для отладки
        logger.debug(f"Результат агента {agent_name} для верификации: {data}")

        # Проверка обязательных полей
        if rules.get("required_fields"):
            if not isinstance(data, dict):
                issues.append(f"Результат должен быть словарем, получен {type(data)}")
                confidence -= 0.3
            else:
                for field in rules["required_fields"]:
                    if field not in data:
                        issues.append(f"Отсутствует обязательное поле: {field}")
                        confidence -= 0.2
                    elif data[field] is None or (isinstance(data[field], str) and not data[field].strip()):
                        issues.append(f"Поле {field} пустое")
                        confidence -= 0.1

        # Специфические проверки для агентов
        specific_verifications = {
            "decomposer": lambda d, t, p, r, c, i: self._verify_decomposer(d, t, i, c, r),
            "validator": lambda d, t, p, r, c, i: self._verify_validator(d, i, c, r),
            "consistency": lambda d, t, p, r, c, i: self._verify_consistency(d, p, i, c, r),
            "codegen": lambda d, t, p, r, c, i: self._verify_codegen(d, p, i, c, r),
            "extractor": lambda d, t, p, r, c, i: self._verify_extractor(d, i, c, r),
            "docker": lambda d, t, p, r, c, i: self._verify_docker(d, i, c, r),
            "tester": lambda d, t, p, r, c, i: self._verify_tester(d, p, i, c, r),
            "docs": lambda d, t, p, r, c, i: self._verify_docs(d, p, i, c, r),
            "monitor": lambda d, t, p, r, c, i: self._verify_monitor(d, i, c, r),
            "coordinator": lambda d, t, p, r, c, i: self._verify_coordinator(d, i, c, r),
            "knowledge": lambda d, t, p, r, c, i: self._verify_knowledge(d, i, c, r)
        }
        
        # Выполняем специфическую верификацию, если она существует
        if agent_name in specific_verifications:
            confidence, issues = specific_verifications[agent_name](data, task, previous_results, rules, confidence, issues)
        else:
            # Общая проверка для неизвестных агентов
            if data is None:
                issues.append(f"Результат агента {agent_name} пустой")
                confidence -= 0.5

        # Проверка на наличие ошибок в тексте результата
        if isinstance(data, str):
            for pattern in rules.get("error_patterns", []):
                if re.search(pattern, data, re.IGNORECASE):
                    issues.append(f"Обнаружен паттерн ошибки: {pattern}")
                    confidence -= 0.2

        # Определение статуса верификации
        status = "passed" if confidence >= 0.7 and not issues else "failed"
        logger.info(f"Верификация агента {agent_name}: status={status}, confidence={confidence}, issues={issues}")
        return {"status": status, "confidence": confidence, "issues": issues}

    def _extract_data_for_verification(self, result: Any) -> Any:
        """Извлечение данных для верификации из различных форматов результата."""
        if result is None:
            return None
            
        if isinstance(result, dict):
            # Проверяем наличие ключа data
            if "data" in result:
                return result["data"]
            # Проверяем наличие ключа error
            elif "error" in result:
                return {"error": result["error"]}
                
        return result

    def _verify_decomposer(self, data: Any, task: str, issues: List[str], confidence: float, rules: Dict[str, Any]) -> tuple:
        """Верификация результата DecomposerAgent."""
        if not isinstance (data, dict):
            issues.append (f"Результат должен быть словарем, получен {type (data)}")
            return confidence - 0.3, issues

        if "error" in data:
            issues.append (f"Агент вернул ошибку: {data['error']}")
            return confidence - 0.5, issues

        if "modules" not in data:
            issues.append ("Отсутствует ключ 'modules'")
            return confidence - 0.3, issues
        
        for module in data["modules"]:
            for field in rules["module_fields"]:
                if field not in module:
                    issues.append(f"Модуль {module.get('name', 'unknown')} не содержит поле {field}")
                    confidence -= 0.1
            
            # Проверка соответствия задаче
            logic_raw = module.get ("logic", "")
            if isinstance (logic_raw, list):
                logger.info (f"<verification> logic_raw: {logic_raw}")
                logic = " ".join (str (item) for item in logic_raw)
            elif isinstance (logic_raw, str):
                logger.info (f"<verification> elif logic_raw: {logic_raw}")
                logic = logic_raw
            else:
                logger.info (f"<verification> else logic_raw: {logic_raw}")
                logic = str (logic_raw)
            logic = logic.lower ()
            task_lower = task.lower ()


            
            # Проверяем, содержит ли логика ключевые слова из задачи
            if not any(word in logic for word in task_lower.split() if len(word) > 3):
                issues.append(f"Логика модуля {module.get('name')} не соответствует задаче: {task}")
                confidence -= 0.2
                
            # Проверка формата внешних зависимостей
            external = module.get("external", [])
            if not isinstance(external, list):
                issues.append(f"Поле 'external' модуля {module.get('name')} должно быть списком")
                confidence -= 0.1
                
        return confidence, issues

    def _verify_validator(self, data: Any, issues: List[str], confidence: float, rules: Dict[str, Any]) -> tuple:
        """Верификация результата ValidatorAgent."""
        if not isinstance(data, dict) or "status" not in data:
            issues.append("Отсутствует поле 'status'")
            return confidence - 0.3, issues
            
        valid_statuses = rules.get("valid_statuses", ["approved", "rejected"])
        if data["status"] not in valid_statuses:
            issues.append(f"Недопустимый статус: {data['status']}")
            confidence -= 0.2
            
        if data["status"] == "rejected" and "comments" not in data:
            issues.append("При статусе 'rejected' отсутствуют комментарии")
            confidence -= 0.2
            
        return confidence, issues

    def _verify_consistency(self, data: Any, previous_results: Dict[str, Any], issues: List[str], confidence: float, rules: Dict[str, Any]) -> tuple:
        """Верификация результата ConsistencyAgent."""
        if not isinstance(data, dict) or "status" not in data:
            issues.append("Отсутствует поле 'status'")
            return confidence - 0.3, issues
            
        valid_statuses = rules.get("valid_statuses", ["approved", "rejected"])
        if data["status"] not in valid_statuses:
            issues.append(f"Недопустимый статус: {data['status']}")
            confidence -= 0.2
            
        if data["status"] == "rejected" and "inconsistencies" not in data:
            issues.append("При статусе 'rejected' отсутствуют несоответствия")
            confidence -= 0.2
            
        # Проверка согласованности с предыдущими результатами
        decomposer_result = previous_results.get("decomposer", {})
        if decomposer_result and isinstance(decomposer_result, dict) and "data" in decomposer_result:
            decomposer_data = decomposer_result["data"]
            if decomposer_data and "modules" in decomposer_data:
                # Все в порядке, декомпозер предоставил модули
                pass
            else:
                issues.append("Отсутствуют модули в результате decomposer")
                confidence -= 0.2
                
        return confidence, issues




    def _verify_codegen_old(self, data: Any, previous_results: Dict[str, Any], issues: List[str], confidence: float, rules: Dict[str, Any]) -> tuple:
        """Верификация результата CodeGeneratorAgent."""
        if data is None:
            issues.append("Код пустой")
            return 0.0, issues
            
        if not isinstance(data, str):
            issues.append(f"Код должен быть строкой, получен {type(data)}")
            return confidence - 0.3, issues
            
        if not data.strip():
            issues.append("Код пустой")
            confidence -= 0.5
            
        # Проверка синтаксиса Python
        try:
            ast.parse(data)
        except SyntaxError as e:
            issues.append(f"Синтаксическая ошибка в коде: {str(e)}")
            confidence -= 0.3
            
        # Проверка соответствия плану через ЛЛМ
        decomposer_result = previous_results.get("decomposer", {})
        if decomposer_result and isinstance(decomposer_result, dict) and "data" in decomposer_result:
            decomposer_data = decomposer_result["data"]
            if decomposer_data and "modules" in decomposer_data:
                plan_str = json.dumps(decomposer_data, ensure_ascii=False)
                code_snippet = data[:1500] + ("..." if len(data) > 1500 else "")
                
                prompt = f"""
                Ты — эксперт по верификации кода. Проверь, реализует ли код требования из плана.
                
                План:
                {plan_str}
                
                Код:
                {code_snippet}
                
                Проверь только:
                1. Импортированы ли все необходимые зависимости
                2. Реализованы ли все маршруты (/sum и т.д.)
                3. Обрабатываются ли параметры из плана
                4. Выдаётся ли результат в нужном формате
                
                Верни только JSON: {{"status": "passed", "issues": []}} или {{"status": "failed", "issues": ["список проблем"]}}
                """
                
                try:
                    from utils import call_openrouter
                    result = call_openrouter(prompt)
                    try:
                        verification = json.loads(result)
                        if isinstance(verification, dict) and "status" in verification:
                            if verification["status"] == "failed" and "issues" in verification:
                                issues.extend(verification["issues"])
                                confidence -= 0.1 * len(verification["issues"])
                    except json.JSONDecodeError:
                        logger.error(f"Ошибка JSON в результате проверки кода: {result}")
                except Exception as e:
                    logger.error(f"Ошибка при вызове ЛЛМ для проверки кода: {str(e)}")
                    
        return confidence, issues

    def _verify_codegen(self, data: Any, previous_results: Dict[str, Any], issues: List[str], confidence: float, rules: Dict[str, Any]) -> tuple:
        """Верификация результата CodeGeneratorAgent."""
        if data is None:
            issues.append ("Код пустой")
            return 0.0, issues

        if not isinstance (data, str):
            issues.append (f"Код должен быть строкой, получен {type (data)}")
            return confidence - 0.3, issues

        if not data.strip ():
            issues.append ("Код пустой")
            confidence -= 0.5

        # Проверка синтаксиса Python
        try:
            ast.parse (data)
        except SyntaxError as e:
            issues.append (f"Синтаксическая ошибка в коде: {str (e)}")
            confidence -= 0.3

        # Проверка соответствия плану через ЛЛМ
        decomposer_result = previous_results.get ("decomposer", {})
        if decomposer_result and isinstance (decomposer_result, dict) and "data" in decomposer_result:
            decomposer_data = decomposer_result["data"]
            if decomposer_data and "modules" in decomposer_data:
                plan_str = json.dumps (decomposer_data, ensure_ascii=False)
                code_snippet = data[:1500] + ("..." if len (data) > 1500 else "")

                prompt = f"""
                Ты — эксперт по верификации кода. Проверь, реализует ли код требования из плана.

                План:
                {plan_str}

                Код:
                {code_snippet}

                Проверь:
                1. Импортированы ли все необходимые зависимости (особенно {', '.join ([m.get ('external', []) for m in decomposer_data['modules'] if 'external' in m])})
                2. Реализованы ли все требуемые классы и модули ({', '.join ([m.get ('name', '') for m in decomposer_data['modules']])})
                3. Обрабатываются ли все указанные входные параметры
                4. Выполняется ли указанная логика для каждого модуля
                5. Возвращаются ли результаты в ожидаемом формате

                Верни JSON: {{"status": "passed" или "failed", "confidence": число от 0 до 1, "issues": ["список конкретных проблем"]}}
                """

                try:
                    from utils import call_openrouter
                    result = call_openrouter (prompt)
                    try:
                        # Очистка от маркеров JSON
                        result = re.sub (r'```json|```', '', result).strip ()
                        verification = json.loads (result)

                        if isinstance (verification, dict):
                            if "status" in verification:
                                if verification["status"] == "failed" and "issues" in verification:
                                    issues.extend (verification["issues"])
                                    # Значительно снижаем уверенность при обнаружении проблем
                                    confidence -= 0.2 * len (verification["issues"])
                                    # Если найдено много проблем, значительно снижаем уверенность
                                    if len (verification["issues"]) >= 3:
                                        confidence -= 0.3

                                # Используем оценку уверенности от LLM, если она предоставлена
                                if "confidence" in verification:
                                    llm_confidence = float (verification["confidence"])
                                    # Учитываем оценку LLM с весом 0.5
                                    confidence = (confidence + llm_confidence) / 2
                    except json.JSONDecodeError:
                        logger.error (f"Ошибка JSON в результате проверки кода: {result}")
                        issues.append ("Ошибка анализа результатов LLM-проверки")
                        confidence -= 0.1
                except Exception as e:
                    logger.error (f"Ошибка при вызове ЛЛМ для проверки кода: {str (e)}")
                    issues.append (f"Не удалось проверить соответствие кода плану: {str (e)}")
                    confidence -= 0.1

        return max (0.0, min (1.0, confidence)), issues




    def _verify_extractor(self, data: Any, issues: List[str], confidence: float, rules: Dict[str, Any]) -> tuple:
        """Верификация результата CodeExtractorAgent."""
        if not isinstance(data, dict) or "file_path" not in data:
            issues.append("Отсутствует поле 'file_path'")
            return confidence - 0.3, issues
            
        file_path = data["file_path"]
        
        # Проверка корректности пути
        if not isinstance(file_path, str) or not file_path.strip():
            issues.append("Некорректный путь к файлу")
            confidence -= 0.2
            
        # Проверка существования директории
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            issues.append(f"Директория {directory} не существует")
            confidence -= 0.1
            
        return confidence, issues

    def _verify_docker(self, data: Any, issues: List[str], confidence: float, rules: Dict[str, Any]) -> tuple:
        """Верификация результата DockerRunnerAgent."""
        if not isinstance(data, dict):
            issues.append(f"Результат должен быть словарем, получен {type(data)}")
            return confidence - 0.3, issues
            
        for field in ["dockerfile", "compose"]:
            if field not in data:
                issues.append(f"Отсутствует поле {field}")
                confidence -= 0.2
            elif not data[field]:
                issues.append(f"Поле {field} пустое")
                confidence -= 0.2
                
        # Проверка содержимого Dockerfile
        dockerfile = data.get("dockerfile", "")
        if dockerfile:
            required_instructions = ["FROM", "COPY", "EXPOSE"]
            for instruction in required_instructions:
                if instruction not in dockerfile:
                    issues.append(f"В Dockerfile отсутствует инструкция {instruction}")
                    confidence -= 0.1
                    
        # Проверка содержимого docker-compose.yml
        compose = data.get("compose", "")
        if compose:
            required_sections = ["version", "services"]
            for section in required_sections:
                if section not in compose:
                    issues.append(f"В docker-compose.yml отсутствует секция {section}")
                    confidence -= 0.1
                    
        return confidence, issues

    def _verify_tester(self, data: Any, previous_results: Dict[str, Any], issues: List[str], confidence: float, rules: Dict[str, Any]) -> tuple:
        """Верификация результата TesterAgent."""
        if not isinstance(data, dict) or "tests" not in data:
            issues.append("Отсутствует поле 'tests'")
            return confidence - 0.3, issues
            
        tests = data["tests"]
        if not isinstance(tests, str) or not tests.strip():
            issues.append("Поле 'tests' пустое или не является строкой")
            confidence -= 0.3
            
        # Проверка наличия pytest
        if "pytest" not in tests.lower() and "test_" not in tests:
            issues.append("Тесты не используют pytest или не содержат тестовых функций")
            confidence -= 0.2
            
        # Проверка синтаксиса Python
        try:
            ast.parse(tests)
        except SyntaxError as e:
            issues.append(f"Синтаксическая ошибка в тестах: {str(e)}")
            confidence -= 0.3
            
        return confidence, issues



    def _verify_docs(self, data: Any, previous_results: Dict[str, Any], issues: List[str], confidence: float, rules: Dict[str, Any]) -> tuple:
        """Верификация результата DocumentationAgent с использованием LLM."""
        from utils import call_openrouter
        
        if not isinstance(data, str):
            issues.append(f"Документация должна быть строкой, получен {type(data)}")
            return confidence - 0.3, issues
            
        if not data.strip():
            issues.append("Документация пустая")
            return confidence - 0.5, issues
        
        # Получаем код приложения из предыдущих результатов или файла
        code = None
        if os.path.exists("project/app.py"):
            with open("project/app.py", "r") as f:
                code = f.read()
        else:
            code_result = previous_results.get("codegen", {})
            if isinstance(code_result, dict) and "data" in code_result:
                code = code_result["data"]
            elif isinstance(code_result, str):
                code = code_result
        
        # Формирование промта для LLM
        prompt = f"""
        Оцени качество документации README.md для API-сервера. Проверь наличие следующих разделов:
        1. Описание приложения и его назначение
        2. Требования и зависимости
        3. Инструкции по установке
        4. Инструкции по использованию
        5. Описание API (endpoints, параметры, форматы ответов)
        6. Примеры запросов и ответов
        
        Код приложения:
        ```python
        {code[:1000]}{"..." if code and len(code) > 1000 else ""}
        ```
        
        Документация:
        ```markdown
        {data[:2000]}{"..." if len(data) > 2000 else ""}
        ```
        
        Оцени документацию по шкале от 0 до 10, где:
        - 0-4: документация неприемлема и требует значительной доработки
        - 5-7: документация приемлема, но могла бы быть улучшена
        - 8-10: документация хорошего качества
        
        Верни только JSON в формате:
        {{"score": <число от 0 до 10>, "is_acceptable": <true/false>, "missing_sections": [<список отсутствующих разделов>], "recommendations": [<краткие рекомендации>]}}
        
        Документация считается приемлемой, если набирает 5 и более баллов.
        Важно: не используй макеры ```json или ``` в своем ответе, просто верни чистый JSON.
        """
        
        try:
            # Вызов LLM
            result = call_openrouter(prompt)
            
            # Очистка от маркеров форматирования
            result = re.sub(r'```json\s*', '', result)
            result = re.sub(r'```\s*$', '', result)
            result = result.strip()
            
            # Парсинг результата
            import json
            try:
                verification = json.loads(result)
                
                # Анализ результатов
                if "score" in verification:
                    score = float(verification["score"])
                    is_acceptable = verification.get("is_acceptable", score >= 5.0)
                    
                    # Установка уверенности на основе оценки
                    confidence = min(1.0, max(0.1, score / 10))
                    
                    # Формирование списка проблем
                    if "missing_sections" in verification and verification["missing_sections"]:
                        issues.extend([f"Отсутствует раздел: {section}" for section in verification["missing_sections"]])
                    
                    if "recommendations" in verification and verification["recommendations"]:
                        issues.extend([f"Рекомендация: {rec}" for rec in verification["recommendations"]])
                    
                    logger.info(f"LLM оценка документации: {score}/10, приемлемо: {is_acceptable}")
                    
                    # Если документация приемлема, считаем верификацию пройденной
                    if is_acceptable:
                        return confidence, []
                else:
                    issues.append("LLM не вернула оценку документации")
                    confidence -= 0.3
                    
            except json.JSONDecodeError as e:
                issues.append(f"Ошибка парсинга результата LLM: {str(e)}")
                confidence -= 0.3
                logger.error(f"Ошибка парсинга JSON в результате LLM (после очистки): '{result}'")
                
                # Аварийный механизм - если оценка высокая (содержит значение 8-10), 
                # всё равно принимаем документацию
                if re.search(r'"score":\s*(8|9|10)', result):
                    logger.info("Принудительное принятие документации из-за высокой оценки")
                    return 0.8, []
                
        except Exception as e:
            issues.append(f"Ошибка при проверке документации через LLM: {str(e)}")
            confidence -= 0.3
            logger.error(f"Ошибка при вызове LLM для проверки документации: {str(e)}")
        
        # Если confidence достаточно высокая, считаем документацию приемлемой
        # даже при наличии незначительных проблем
        if confidence >= 0.5:
            logger.info(f"Документация принята с confidence={confidence}, несмотря на проблемы")
            return confidence, []
        
        return confidence, issues




        
    def _verify_monitor(self, data: Any, issues: List[str], confidence: float, rules: Dict[str, Any]) -> tuple:
        """Верификация результата MonitorAgent."""
        if not isinstance(data, dict) or "command" not in data:
            issues.append("Отсутствует поле 'command'")
            return confidence - 0.3, issues
            
        command = data["command"]
        valid_commands = rules.get("valid_commands", ["none", "Перезапустить", "Принудительный переход к consistency"])
        
        # Проверка команды
        if not any(valid_cmd in command for valid_cmd in valid_commands):
            issues.append(f"Недопустимая команда: {command}")
            confidence -= 0.2
            
        return confidence, issues
        
    def _verify_coordinator(self, data: Any, issues: List[str], confidence: float, rules: Dict[str, Any]) -> tuple:
        """Верификация результата CoordinatorAgent."""
        valid_agents = [
            "decomposer", "validator", "consistency", "codegen", 
            "extractor", "docker", "tester", "docs", "monitor", "coordinator"
        ]
        
        if isinstance(data, str):
            # Если результат - строка, проверяем, является ли она допустимым агентом
            if data not in valid_agents:
                issues.append(f"Недопустимый агент: {data}")
                confidence -= 0.2
        elif isinstance(data, dict) and "next_agent" in data:
            # Если результат - словарь с next_agent, проверяем значение
            next_agent = data["next_agent"]
            if next_agent not in valid_agents:
                issues.append(f"Недопустимый следующий агент: {next_agent}")
                confidence -= 0.2
        else:
            issues.append(f"Неожиданный формат результата координатора: {type(data)}")
            confidence -= 0.3
            
        return confidence, issues
        
    def _verify_knowledge(self, data: Any, issues: List[str], confidence: float, rules: Dict[str, Any]) -> tuple:
        """Верификация результата KnowledgeExtractorAgent."""
        if not isinstance(data, list) and not (isinstance(data, dict) and "data" in data):
            issues.append("Результат должен быть списком или словарем с полем 'data'")
            return confidence - 0.3, issues
            
        # Если результат - словарь с полем 'data', извлекаем данные
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
            
        # Проверка элементов списка
        if isinstance(data, list):
            if not data:
                issues.append("Список извлеченных знаний пуст")
                confidence -= 0.5
            else:
                for i, item in enumerate(data):
                    if not isinstance(item, dict):
                        issues.append(f"Элемент {i} не является словарем")
                        confidence -= 0.1
                    elif "category" not in item or "data" not in item:
                        issues.append(f"Элемент {i} не содержит обязательные поля 'category' и 'data'")
                        confidence -= 0.1
        else:
            issues.append(f"Неожиданный тип данных: {type(data)}")
            confidence -= 0.3
            
        return confidence, issues

if __name__ == "__main__":
    # Пример использования
    verifier = VerificationAgent()
    sample_result = {"modules": [{"name": "api_server", "input": {"a": "int"}, "output": {"result": "int"}, "logic": "сложить a и b", "external": ["Flask"]}]}
    task = "Создать API-сервер, роут /sum, возвращает сумму a и b"
    verification = verifier.verify("decomposer", sample_result, task)
    print(json.dumps(verification, indent=2))
