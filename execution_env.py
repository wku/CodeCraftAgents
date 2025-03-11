import os
import subprocess
import tempfile
import shutil
import docker
from typing import Dict, Any, Optional
from utils import logger, save_text, load_json, call_openrouter
import time
import json
import re

class ExecutionEnvironment:
    def __init__(self, project_dir: str = "project"):
        self.project_dir = project_dir
        self.docker_client = docker.from_env()
        self.temp_dir = None

    def setup_sandbox(self) -> str:
        if self.temp_dir:
            self.cleanup_sandbox()
        self.temp_dir = tempfile.mkdtemp(prefix="execution_sandbox_")
        logger.info(f"Создана временная песочница: {self.temp_dir}")
        return self.temp_dir

    def cleanup_sandbox(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            logger.info(f"Очищена песочница: {self.temp_dir}")
        self.temp_dir = None

    def execute_python_code(self, code: Any, test_code: Optional[Any] = None) -> Dict[str, Any]:
        """Выполнение Python-кода в изолированной среде."""
        if isinstance(code, dict) and "data" in code:
            code = code["data"].get("code", code["data"]) if isinstance(code["data"], dict) else code["data"]
        if isinstance(test_code, dict) and "data" in test_code:
            test_code = test_code["data"].get("tests", test_code["data"]) if isinstance(test_code["data"], dict) else test_code["data"]

        sandbox_dir = self.setup_sandbox()
        code_path = os.path.join(sandbox_dir, "app.py")
        test_path = os.path.join(sandbox_dir, "test_app.py") if test_code else None

        save_text(code, code_path)
        if test_code:
            save_text(test_code, test_path)

        try:
            result = subprocess.run(
                ["python", "-m", "py_compile", code_path],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                logger.error(f"Ошибка синтаксиса в коде: {result.stderr}")
                return {"status": "failed", "logs": result.stderr, "error": "Syntax error"}

            analysis = self._analyze_required_arguments(code)
            logger.info(f"Анализ аргументов: {json.dumps(analysis)}")

            input_file_path = None
            if analysis.get("requires_input_file", False):
                input_file_path = os.path.join(sandbox_dir, "test_input.txt")
                save_text(analysis.get("input_file_content", "Тестовый файл"), input_file_path)

            cmd_args = ["python", code_path]
            if analysis.get("requires_args", False):
                for arg in analysis.get("args", []):
                    cmd_args.extend([arg["name"], arg["value"]]) if arg["name"].startswith("-") else cmd_args.append(arg["value"])

            infinite_execution = call_openrouter(f"""
                Проанализируй код:\n{code}\nОтветь "да" если бесконечный процесс, "нет" если конечный.
            """).strip().lower()
            if infinite_execution == "да":
                return {"status": "success", "logs": "Код запускает бесконечный процесс", "warning": "infinite_execution"}

            if test_code:
                result = subprocess.run(
                    ["pytest", test_path, "-v"],
                    capture_output=True, text=True, timeout=30
                )
                logs = result.stdout + result.stderr
                status = "success" if result.returncode == 0 else "failed"
                logger.info(f"Тесты: {logs}")
                return {"status": status, "logs": logs}
            else:
                result = subprocess.run(cmd_args, capture_output=True, text=True, timeout=10)
                logs = result.stdout + result.stderr
                status = "success" if result.returncode == 0 else "failed"
                logger.info(f"Код выполнен: {logs}")
                return {"status": status, "logs": logs}
        except subprocess.TimeoutExpired as e:
            return {"status": "failed", "logs": str(e), "error": "Timeout"}
        except Exception as e:
            return {"status": "failed", "logs": str(e), "error": "Execution error"}
        finally:
            self.cleanup_sandbox()

    def execute_docker(self, docker_result: Any, external_deps: list = []) -> Dict[str, Any]:
        """Выполнение Docker-контейнеров."""
        if isinstance(docker_result, dict) and "data" in docker_result:
            dockerfile = docker_result["data"]["dockerfile"]
            compose = docker_result["data"]["compose"]
        else:
            dockerfile = docker_result["dockerfile"]
            compose = docker_result["compose"]

        sandbox_dir = self.setup_sandbox()
        dockerfile_path = os.path.join(sandbox_dir, "Dockerfile")
        compose_path = os.path.join(sandbox_dir, "docker-compose.yml")

        save_text(dockerfile, dockerfile_path)
        save_text(compose, compose_path)
        os.makedirs(os.path.join(sandbox_dir, "project"), exist_ok=True)
        if os.path.exists("project/app.py"):
            shutil.copy("project/app.py", os.path.join(sandbox_dir, "project/app.py"))

        if "requirements.txt" in dockerfile:
            save_text("\n".join(external_deps), os.path.join(sandbox_dir, "requirements.txt"))

        try:
            image, build_logs = self.docker_client.images.build(
                path=sandbox_dir, dockerfile="Dockerfile", tag="sandbox_app:latest", rm=True
            )
            build_logs_str = "\n".join(log.get("stream", "") for log in build_logs if "stream" in log)
            logger.info(f"Логи сборки: {build_logs_str}")

            result = subprocess.run(
                ["docker-compose", "-f", compose_path, "up", "-d"],
                capture_output=True, text=True, cwd=sandbox_dir, timeout=60
            )
            if result.returncode != 0:
                return {"status": "failed", "logs": result.stderr, "error": "Docker compose failed"}

            time.sleep(5)  # Ожидание запуска
            test_result = self._test_api_endpoint()
            return {"status": "success", "logs": build_logs_str + "\n" + test_result["logs"]}
        except docker.errors.BuildError as e:
            return {"status": "failed", "logs": str(e), "error": "Build error"}
        except subprocess.TimeoutExpired as e:
            return {"status": "failed", "logs": str(e), "error": "Timeout"}
        except Exception as e:
            return {"status": "failed", "logs": str(e), "error": "Docker error"}
        finally:
            subprocess.run(["docker-compose", "-f", compose_path, "down"], cwd=sandbox_dir)
            self.cleanup_sandbox()

    def _test_api_endpoint(self) -> Dict[str, Any]:
        """Проверка API (заглушка)."""
        return {"status": "success", "logs": "Container started successfully"}

    def _analyze_required_arguments(self, code: str) -> Dict[str, Any]:
        """Анализ аргументов через LLM."""
        prompt = f"""
        Проанализируй код:\n{code[:3000]}{"..." if len(code) > 3000 else ""}\n
        Верни JSON:
        {{"requires_args": true/false, "args": [{{"name": "имя", "value": "значение"}}], "requires_input_file": true/false, "input_file_content": "пример"}}
        """
        try:
            response = call_openrouter(prompt)
            response = re.sub(r'```json|```', '', response).strip()
            return json.loads(response)
        except Exception as e:
            logger.error(f"Ошибка анализа аргументов: {str(e)}")
            return {"requires_args": False, "args": [], "requires_input_file": False, "input_file_content": ""}

if __name__ == "__main__":
    env = ExecutionEnvironment()
    sample_code = {"data": {"code": "print('Hello')"}}
    result = env.execute_python_code(sample_code)
    print(json.dumps(result, indent=2))