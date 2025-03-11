from typing import Dict, Any
from utils import call_openrouter, logger
from base_agent import BaseAgent

class CoordinatorAgent(BaseAgent):
    def run(self, source: str, data: Any) -> str:
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
        data_str = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
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
        next_agent = call_openrouter(prompt).strip()
        if source in expected_flow:
            if next_agent not in expected_flow.values():
                logger.warning(f"Координатор предложил {next_agent}, что не является допустимым агентом")
                next_agent = expected_flow[source]
        return next_agent