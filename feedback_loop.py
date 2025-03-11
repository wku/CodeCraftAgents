# feedback_loop.py
import json
import time
import os
from typing import Dict, Any, Optional, List
from verification import VerificationAgent
from utils import logger, load_json, save_json

from utils import logger, load_json, save_json, load_yaml

from agents.request_validation_agent import RequestValidationAgent
from agents.decomposer_agent import DecomposerAgent
from agents.validator_agent import ValidatorAgent
from agents.consistency_agent import ConsistencyAgent
from agents.code_generator_agent import CodeGeneratorAgent
from agents.code_extractor_agent import CodeExtractorAgent
from agents.docker_runner_agent import DockerRunnerAgent
from agents.knowledge_extractor_agent import KnowledgeExtractorAgent
from agents.coordinator_agent import CoordinatorAgent
from agents.monitor_agent import MonitorAgent
from agents.tester_agent import TesterAgent
from agents.documentation_agent import DocumentationAgent



class FeedbackLoop:
    def __init__(self, config_path: str = "settings.yml", rules_path: str = "settings.yml"):
        """Инициализация цикла обратной связи."""
        self.config_path = config_path
        self.rules_path = rules_path
        settings = load_yaml(config_path)
        self.config = settings.get('feedback', {})
        self.verifier = VerificationAgent(rules_path)

        # Инициализация агентов
        self.agents = {
            "request_validation": RequestValidationAgent(),
            "decomposer": DecomposerAgent(),
            "validator": ValidatorAgent(),
            "consistency": ConsistencyAgent(),
            "codegen": CodeGeneratorAgent(),
            "extractor": CodeExtractorAgent(),
            "docker": DockerRunnerAgent(),
            "knowledge": KnowledgeExtractorAgent(),#todo
            "coordinator": CoordinatorAgent(), #todo
            "monitor": MonitorAgent(), #todo
            "tester": TesterAgent(),
            "docs": DocumentationAgent()
        }
        self.previous_results = {}
        self._load_previous_results()

    def _load_previous_results(self):
        """Загрузка сохраненных результатов из директории project."""
        state_path = "project/state.json"
        if os.path.exists(state_path):
            state = load_json(state_path)
            if state and "previous_results" in state:
                self.previous_results = state["previous_results"]
                logger.info(f"Загружены предыдущие результаты из {state_path}")

    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Получение специфической конфигурации для агента."""
        base_config = {
            "max_iterations": self.config.get("max_iterations", 3),
            "confidence_threshold": self.config.get("confidence_threshold", 0.7),
            "retry_delay": self.config.get("retry_delay", 2)
        }
        agent_specific = self.config.get("agent_specific", {})
        base_config.update(agent_specific.get(agent_name, {}))
        return base_config

    def run_agent_with_feedback(self, agent_name: str, input_data: Any, task: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Запуск агента с обратной связью."""
        agent_config = self.get_agent_config(agent_name)
        iterations = 0
        max_iterations = agent_config["max_iterations"]
        confidence_threshold = agent_config["confidence_threshold"]
        retry_delay = agent_config["retry_delay"]

        while iterations < max_iterations:
            logger.info(f"Запуск агента {agent_name}, итерация {iterations + 1}/{max_iterations}")
            agent = self.agents.get(agent_name)
            if not agent:
                logger.error(f"Агент {agent_name} не найден")
                return {"error": f"Unknown agent: {agent_name}", "source": agent_name}

            processed_input = self._prepare_input_data(agent_name, input_data)

            try:
                if agent_name in ["request_validation", "decomposer"]:
                    result = agent.run(task)
                elif agent_name == "docker":
                    file_path = processed_input.get("file_path", "project/app.py") if isinstance(processed_input, dict) else "project/app.py"
                    external = self._get_external_dependencies()
                    result = agent.run(file_path, external)
                elif agent_name == "tester":
                    codegen_result = self.previous_results.get("codegen", {})
                    plan = self.previous_results.get("decomposer", {})
                    result = agent.run(plan, codegen_result)
                elif agent_name == "docs":
                    plan = self.previous_results.get("decomposer", {})
                    code = self.previous_results.get("codegen", {})
                    result = agent.run(plan, code)
                elif agent_name == "coordinator":
                    source = state.get("current_agent", "unknown")
                    result = agent.run(source, processed_input)
                elif agent_name == "monitor":
                    result = agent.run(state)
                else:
                    logger.info (f"################################")
                    logger.info (f"<FeedbackLoop.run_agent_with_feedback> processed_input: {processed_input}")
                    logger.info (f"################################")
                    result = agent.run(processed_input)
                    logger.info (f"<FeedbackLoop.run_agent_with_feedback> result: {result}")

            except Exception as e:
                logger.error(f"Ошибка выполнения агента {agent_name}: {str(e)}")
                return {"error": str(e), "source": agent_name, "type": "execution_error"}

            verification = self.verifier.verify(agent_name, result, task, self.previous_results)
            confidence = result.get("confidence", verification["confidence"])

            self.previous_results[agent_name] = result
            if verification["status"] == "passed":
                state["data"] = result
                state["verification"] = verification
                save_json(state, "project/state.json")

            if verification["status"] == "passed" and confidence >= confidence_threshold:
                logger.info(f"Агент {agent_name} успешно завершил работу с уверенностью {confidence}")
                return result
            else:
                logger.warning(f"Агент {agent_name} не прошёл верификацию: confidence={confidence}, issues={verification['issues']}")
                iterations += 1
                if iterations < max_iterations:
                    logger.info(f"Повторная попытка для агента {agent_name} после задержки {retry_delay} сек")
                    time.sleep(retry_delay)
                    if verification["issues"] and agent_name in ["decomposer", "codegen"]:
                        input_data = f"{task}. Уточнение: {', '.join(verification['issues'])}"
                else:
                    logger.error(f"Агент {agent_name} исчерпал лимит итераций ({max_iterations})")
                    break

        return self._handle_failure(agent_name, result, verification)

    def _prepare_input_data(self, agent_name: str, input_data: Any) -> Any:
        """Подготовка входных данных для агента с учетом предыдущих результатов."""
        prev_result = self.previous_results.get
        if agent_name in ["request_validation", "decomposer"]:
            return input_data
        elif agent_name in ["validator", "consistency", "codegen"]:
            return prev_result("decomposer", input_data)
        elif agent_name == "extractor":
            return prev_result("codegen", input_data)
        elif agent_name == "docker":
            file_path = input_data.get("file_path", "project/app.py") if isinstance(input_data, dict) else "project/app.py"
            external = self._get_external_dependencies()
            return {"file_path": file_path, "external": external}
        return input_data

    def _get_external_dependencies(self) -> List[str]:
        """Получение внешних зависимостей из результатов decomposer."""
        decomposer_result = self.previous_results.get("decomposer", {})
        if "data" in decomposer_result and "modules" in decomposer_result["data"]:
            return decomposer_result["data"]["modules"][0].get("external", [])
        return ["Flask"]

    def _handle_failure(self, agent_name: str, result: Any, verification: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка неудачного выполнения агента."""
        logger.warning(f"Обработка неудачи агента {agent_name}: {verification}")
        fallback_agent = self.config.get("fallback_agent", "decomposer")
        if agent_name == "docker":
            return {"error": "Docker verification failed", "issues": verification["issues"], "next_agent": "tester", "confidence": 0.5}
        if agent_name != fallback_agent:
            return {"error": "Verification failed", "next_agent": fallback_agent, "issues": verification["issues"], "confidence": 0.0}
        return {"error": "Critical failure", "source": agent_name, "issues": verification["issues"], "confidence": 0.0}

    def determine_next_agent(self, current_agent: str, result: Any, verification: Dict[str, Any]) -> Optional[str]:
        """Определение следующего агента с учётом верификации."""
        expected_flow = {
            "request_validation": "decomposer",
            "decomposer": "validator",
            "validator": "consistency",
            "consistency": "codegen",
            "codegen": "extractor",
            "extractor": "docker",
            "docker": "tester",
            "tester": "docs",
            "docs": None
        }
        if isinstance(result, dict) and "error" in result and "next_agent" in result:
            return result["next_agent"]
        if current_agent == "coordinator":
            return result if isinstance(result, str) and result in self.agents else "decomposer"
        elif current_agent == "monitor":
            command = result.get("command", "none") if isinstance(result, dict) else "none"
            if "Перезапустить" in command:
                return command.split(" ")[1]
            elif command == "Принудительный переход к consistency":
                return "consistency"
            return "coordinator"
        next_agent = expected_flow.get(current_agent, "coordinator")
        if not next_agent:
            return None
        if verification["status"] == "failed" and verification["confidence"] < 0.5:
            return "decomposer"
        return next_agent

if __name__ == "__main__":
    feedback = FeedbackLoop()
    state = {
        "task": "Создать API-сервер, роут /sum, возвращает сумму a и b",
        "current_agent": "request_validation",
        "data": None,
        "step": 0,
        "validator_consecutive_runs": 0
    }
    result = feedback.run_agent_with_feedback("request_validation", state["task"], state["task"], state)
    print(json.dumps(result, indent=2))
    next_agent = feedback.determine_next_agent("request_validation", result, state["verification"])
    print(f"Следующий агент: {next_agent}")