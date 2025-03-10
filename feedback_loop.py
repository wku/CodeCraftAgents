# feedback_loop.py
import json
import time
import os
from typing import Dict, Any, Optional, List
from verification import VerificationAgent
from utils import logger, load_json, save_json
from agents import initialize_agents  # Предполагается, что agents.py обновлен
from utils import logger, load_json, save_json, load_yaml



class FeedbackLoop:
    def __init__(self, config_path: str = "settings.yml", rules_path: str = "settings.yml"):
        """Инициализация цикла обратной связи."""

        self.config_path = config_path
        self.rules_path = rules_path
        settings = load_yaml(config_path)
        self.config = settings.get('feedback', {})
        self.verification_rules = settings.get('verification_rules', {})
        self.verifier = VerificationAgent(rules_path)

        self.agents = initialize_agents()
        self.previous_results = {}  # Хранение результатов предыдущих агентов
        
        # Загрузка сохраненных результатов для восстановления контекста
        self._load_previous_results()


    def _load_previous_results(self):
        """Загрузка сохраненных результатов из директории project."""
        # Загружаем state.json для восстановления контекста
        state_path = "project/state.json"
        if os.path.exists(state_path):
            state = load_json(state_path)
            if state and "previous_results" in state:
                self.previous_results = state["previous_results"]
                logger.info(f"Загружены предыдущие результаты из {state_path}")

    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Получение специфической конфигурации для агента."""
        # Получаем базовую конфигурацию
        base_config = {
            "max_iterations": self.config.get("max_iterations", 3),
            "confidence_threshold": self.config.get("confidence_threshold", 0.7),
            "retry_delay": self.config.get("retry_delay", 2)
        }
        
        # Переопределяем специфичными настройками для агента, если они есть
        agent_specific = self.config.get("agent_specific", {})
        if agent_name in agent_specific:
            for key, value in agent_specific[agent_name].items():
                base_config[key] = value
                
        return base_config

    def run_agent_with_feedback(self, agent_name: str, input_data: Any, task: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Запуск агента с обратной связью."""
        # Получаем конфигурацию для агента
        agent_config = self.get_agent_config(agent_name)
        iterations = 0
        max_iterations = agent_config["max_iterations"]
        confidence_threshold = agent_config["confidence_threshold"]
        retry_delay = agent_config["retry_delay"]

        while iterations < max_iterations:
            logger.info(f"Запуск агента {agent_name}, итерация {iterations + 1}/{max_iterations}")
            
            # Проверка существования агента
            agent = self.agents.get(agent_name)
            if not agent:
                logger.error(f"Агент {agent_name} не найден")
                return {"error": f"Unknown agent: {agent_name}", "source": agent_name}

            # Подготовка входных данных для агента
            processed_input = self._prepare_input_data(agent_name, input_data)

            # Выполнение агента
            try:
                if agent_name == "decomposer":
                    result = agent.run(task)
                elif agent_name in ["validator", "consistency"]:
                    # Специальная обработка для валидатора и проверки согласованности
                    # Они должны получать данные decomposer в правильном формате
                    if isinstance(processed_input, dict) and "data" in processed_input:
                        result = agent.run(processed_input["data"])
                    else:
                        result = agent.run(processed_input)
                elif agent_name == "codegen":
                    # Кодогенератор должен получать данные из decomposer
                    decomposer_data = self.previous_results.get("decomposer", {})
                    if isinstance(decomposer_data, dict) and "data" in decomposer_data:
                        result = agent.run(decomposer_data["data"])
                    else:
                        result = agent.run(processed_input)
                elif agent_name == "extractor":
                    # Экстрактор получает код из codegen
                    if isinstance(processed_input, dict) and "data" in processed_input:
                        result = agent.run(processed_input["data"])
                    else:
                        result = agent.run(processed_input)
                elif agent_name == "docker":
                    # Docker получает путь к файлу и зависимости
                    file_path = processed_input.get("file_path", "project/app.py") if isinstance(processed_input, dict) else "project/app.py"
                    external = self._get_external_dependencies()
                    result = agent.run(file_path, external)
                elif agent_name == "tester":
                    # Тестер получает код и план
                    codegen_result = self.previous_results.get("codegen", {})
                    plan = self.previous_results.get("decomposer", {})
                    result = agent.run(plan, codegen_result)
                elif agent_name == "docs":
                    # Документатор получает план и код
                    plan = self.previous_results.get("decomposer", {})
                    code = None
                    if os.path.exists("project/app.py"):
                        with open("project/app.py", "r") as f:
                            code = f.read()
                    else:
                        code = self.previous_results.get("codegen", {})
                    result = agent.run(plan, code)
                elif agent_name == "coordinator":
                    source = state.get("current_agent", "unknown")
                    result = agent.run(source, processed_input)
                elif agent_name == "monitor":
                    result = agent.run(state)
                else:
                    result = agent.run(processed_input)
            except Exception as e:
                logger.error(f"Ошибка выполнения агента {agent_name}: {str(e)}")
                # Возвращаем структурированную ошибку для обработки вызывающим кодом
                return {
                    "error": str(e), 
                    "source": agent_name,
                    "type": "execution_error"
                }

            # Верификация результата
            verification = self.verifier.verify(agent_name, result, task, self.previous_results)
            confidence = verification["confidence"]
            issues = verification["issues"]

            # Сохранение результата
            self.previous_results[agent_name] = result
            # Обновляем состояние только если результат прошел верификацию
            if verification["status"] == "passed":
                state["data"] = result
                state["verification"] = verification
                save_json(state, "project/state.json")

            # Проверка уверенности и проблем
            if verification["status"] == "passed" and confidence >= confidence_threshold:
                logger.info(f"Агент {agent_name} успешно завершил работу с уверенностью {confidence}")
                return result
            else:
                logger.warning(f"Агент {agent_name} не прошёл верификацию: confidence={confidence}, issues={issues}")
                iterations += 1
                if iterations < max_iterations:
                    logger.info(f"Повторная попытка для агента {agent_name} после задержки {retry_delay} сек")
                    time.sleep(retry_delay)
                    
                    # Уточнение входных данных на основе проблем
                    if issues and agent_name == "decomposer":
                        input_data = f"{task}. Уточнение: {', '.join(issues)}"
                    elif issues and agent_name == "codegen":
                        # Для кодогенератора добавляем информацию о проблемах
                        decomposer_data = self.previous_results.get("decomposer", {})
                        if isinstance(decomposer_data, dict) and "data" in decomposer_data:
                            plan_str = json.dumps(decomposer_data["data"])
                            input_data = f"План: {plan_str}\nПроблемы предыдущей попытки: {', '.join(issues)}"
                else:
                    logger.error(f"Агент {agent_name} исчерпал лимит итераций ({max_iterations})")
                    break

        # Если не удалось достичь порога уверенности
        return self._handle_failure(agent_name, result, verification)

    def _prepare_input_data(self, agent_name: str, input_data: Any) -> Any:
        """Подготовка входных данных для агента с учетом предыдущих результатов."""
        if agent_name == "decomposer":
            return input_data  # Декомпозер получает оригинальную задачу
        
        elif agent_name == "validator":
            # Validator должен получить результат decomposer
            decomposer_result = self.previous_results.get("decomposer")
            if decomposer_result:
                return decomposer_result
            return input_data
            
        elif agent_name == "consistency":
            # Consistency должен получить результат decomposer после validator
            decomposer_result = self.previous_results.get("decomposer")
            if decomposer_result:
                return decomposer_result
            return input_data
            
        elif agent_name == "codegen":
            # Codegen должен получить результат decomposer после consistency
            decomposer_result = self.previous_results.get("decomposer")
            if decomposer_result:
                return decomposer_result
            return input_data
            
        elif agent_name == "extractor":
            # Extractor должен получить результат codegen
            codegen_result = self.previous_results.get("codegen")
            if codegen_result:
                return codegen_result
            return input_data
            
        elif agent_name == "docker":
            # Подготовка данных для Docker
            if isinstance(input_data, dict) and "file_path" in input_data:
                return input_data
                
            # Если входные данные не содержат file_path, используем стандартный
            file_path = "project/app.py"
            external = self._get_external_dependencies()
            return {"file_path": file_path, "external": external}
            
        # Для других агентов возвращаем входные данные без изменений
        return input_data

    def _get_external_dependencies(self) -> List[str]:
        """Получение внешних зависимостей из результатов decomposer."""
        external = []
        decomposer_result = self.previous_results.get("decomposer")
        
        if decomposer_result:
            if isinstance(decomposer_result, dict):
                if "data" in decomposer_result and isinstance(decomposer_result["data"], dict):
                    modules = decomposer_result["data"].get("modules", [])
                    if modules and len(modules) > 0:
                        external = modules[0].get("external", [])
                        
        # Добавляем Flask, если он не указан
        if "Flask" not in external:
            external.append("Flask")
            
        return external

    def _handle_failure(self, agent_name: str, result: Any, verification: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка неудачного выполнения агента."""
        logger.warning(f"Обработка неудачи агента {agent_name}: {verification}")
        
        # Проверка на особые случаи
        if agent_name == "docker":
            # Для Docker может быть критично отсутствие файла, но это не должно
            # блокировать весь процесс
            return {
                "error": "Docker verification failed",
                "issues": verification["issues"],
                "next_agent": "tester",  # Переходим к тестам, пропуская Docker
                "confidence": 0.5
            }
        
        fallback_agent = self.config["fallback_agent"]
        if agent_name != fallback_agent:
            logger.info(f"Возврат к предыдущему этапу: {fallback_agent}")
            return {
                "error": "Verification failed", 
                "next_agent": fallback_agent, 
                "issues": verification["issues"],
                "confidence": 0.0
            }
        
        # Критическая ошибка в основном агенте
        return {
            "error": "Critical failure", 
            "source": agent_name, 
            "issues": verification["issues"],
            "confidence": 0.0
        }

    def determine_next_agent(self, current_agent: str, result: Any, verification: Dict[str, Any]) -> str:
        """Определение следующего агента с учётом верификации."""
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

        # Проверка наличия информации о переходе в результате ошибки
        if isinstance(result, dict) and "error" in result and "next_agent" in result:
            return result["next_agent"]

        # Особая обработка для координатора
        if current_agent == "coordinator":
            # Coordinator возвращает имя агента напрямую
            if isinstance(result, str) and result in expected_flow:
                return result
            else:
                logger.warning(f"Координатор вернул недопустимого агента: {result}, используется decomposer")
                return "decomposer"
        
        # Особая обработка для монитора
        elif current_agent == "monitor":
            if isinstance(result, dict) and "command" in result:
                command = result["command"]
                if command != "none" and "Перезапустить" in command:
                    # Извлекаем имя агента из команды
                    parts = command.split(" ")
                    if len(parts) > 1 and parts[1] in expected_flow:
                        return parts[1]
                elif command == "Принудительный переход к consistency":
                    return "consistency"
            # По умолчанию продолжаем нормальный поток
            return "coordinator"

        # Стандартный поток для других агентов
        next_agent = expected_flow.get(current_agent, "coordinator")
        if not next_agent:
            logger.info("Все агенты завершены")
            return None
            
        # Проверка верификации
        if verification and verification["status"] == "failed" and verification["confidence"] < 0.5:
            logger.warning(f"Верификация не прошла для {current_agent}, возврат к decomposer")
            return "decomposer"
            
        return next_agent

if __name__ == "__main__":
    # Пример использования
    feedback = FeedbackLoop()
    state = {
        "task": "Создать API-сервер, роут /sum, возвращает сумму a и b",
        "current_agent": "decomposer",
        "data": None,
        "step": 0,
        "validator_consecutive_runs": 0
    }
    result = feedback.run_agent_with_feedback("decomposer", state["task"], state["task"], state)
    print(json.dumps(result, indent=2))
    next_agent = feedback.determine_next_agent("decomposer", result, state["verification"])
    print(f"Следующий агент: {next_agent}")
