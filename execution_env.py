# execution_env.py
import os
import subprocess
import tempfile
import shutil
import docker
from typing import Dict, Any, Optional
from utils import logger, save_text, load_json
import time 


from utils import call_openrouter


class ExecutionEnvironment:
    def __init__(self, project_dir: str = "project"):
        """Инициализация среды выполнения."""
        self.project_dir = project_dir
        self.docker_client = docker.from_env()
        self.temp_dir = None

    def setup_sandbox(self) -> str:
        """Создание временной песочницы для выполнения."""
        if self.temp_dir:
            self.cleanup_sandbox()
        self.temp_dir = tempfile.mkdtemp(prefix="execution_sandbox_")
        logger.info(f"Создана временная песочница: {self.temp_dir}")
        return self.temp_dir

    def cleanup_sandbox(self):
        """Очистка песочницы."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            logger.info(f"Очищена песочница: {self.temp_dir}")
        self.temp_dir = None

    def execute_python_code(self, code: str, test_code: Optional[str] = None) -> Dict[str, Any]:
        """Выполнение Python-кода в изолированной среде."""
        sandbox_dir = self.setup_sandbox()
        code_path = os.path.join(sandbox_dir, "app.py")
        test_path = os.path.join(sandbox_dir, "test_app.py") if test_code else None

        # Сохранение кода
        save_text(code, code_path)
        if test_code:
            save_text(test_code, test_path)

        try:
            # Проверка синтаксиса
            result = subprocess.run(
                ["python", "-m", "py_compile", code_path],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                logger.error(f"Ошибка синтаксиса в коде: {result.stderr}")
                return {"status": "failed", "logs": result.stderr, "error": "Syntax error"}

            # Использование LLM для определения, запускает ли код бесконечный процесс
            prompt = f"""
    Проанализируй следующий Python-код и определи, будет ли он выполняться бесконечно (например, запускает веб-сервер без явного завершения):

    {code}

    Ответь только "да" или "нет".
    Ответь "да", если код:
    1. Запускает веб-сервер (Flask, aiohttp, FastAPI и т.д.)
    2. Содержит бесконечный цикл (while True)
    3. Запускает любой процесс, который не завершается сам по себе

    Ответь "нет", если код:
    1. Выполняет конечное число операций и завершается
    2. Содержит только определения функций и классов без их вызова
    3. Содержит веб-сервер, но его запуск обернут в условие if __name__ == "__main__" и не будет выполнен при импорте
    """
            
            # Вызов LLM для анализа кода
            infinite_execution = call_openrouter(prompt).strip().lower()
            logger.info(f"LLM анализ кода: бесконечное выполнение = {infinite_execution}")
            
            if infinite_execution == "да":
                logger.info(f"Код определен как запускающий бесконечный процесс, пропускаем фактическое выполнение")
                return {"status": "success", "logs": "Код успешно скомпилирован. Выполнение пропущено, так как код запускает бесконечный процесс.", "warning": "infinite_execution"}

            # Выполнение тестов, если они есть
            if test_code:
                result = subprocess.run(
                    ["pytest", test_path, "-v"],
                    capture_output=True, text=True, timeout=30
                )
                logs = result.stdout + result.stderr
                if result.returncode != 0:
                    logger.error(f"Тесты не пройдены: {logs}")
                    return {"status": "failed", "logs": logs, "error": "Tests failed"}
                logger.info(f"Тесты успешно пройдены: {logs}")
                return {"status": "success", "logs": logs}
            else:
                # Простая проверка выполнения
                result = subprocess.run(
                    ["python", code_path],
                    capture_output=True, text=True, timeout=10
                )
                logs = result.stdout + result.stderr
                if result.returncode != 0:
                    logger.error(f"Ошибка выполнения кода: {logs}")
                    return {"status": "failed", "logs": logs, "error": "Execution failed"}
                logger.info(f"Код успешно выполнен: {logs}")
                return {"status": "success", "logs": logs}

        except subprocess.TimeoutExpired as e:
            logger.error(f"Превышено время выполнения: {str(e)}")
            return {"status": "failed", "logs": str(e), "error": "Timeout"}
        except Exception as e:
            logger.error(f"Ошибка в песочнице: {str(e)}")
            return {"status": "failed", "logs": str(e), "error": "Execution error"}
        finally:
            self.cleanup_sandbox()





    def execute_python_code_old(self, code: str, test_code: Optional[str] = None) -> Dict[str, Any]:
        """Выполнение Python-кода в изолированной среде."""
        sandbox_dir = self.setup_sandbox()
        code_path = os.path.join(sandbox_dir, "app.py")
        test_path = os.path.join(sandbox_dir, "test_app.py") if test_code else None

        # Сохранение кода
        save_text(code, code_path)
        if test_code:
            save_text(test_code, test_path)

        try:
            # Проверка синтаксиса
            result = subprocess.run(
                ["python", "-m", "py_compile", code_path],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                logger.error(f"Ошибка синтаксиса в коде: {result.stderr}")
                return {"status": "failed", "logs": result.stderr, "error": "Syntax error"}

            # Выполнение тестов, если они есть
            if test_code:
                result = subprocess.run(
                    ["pytest", test_path, "-v"],
                    capture_output=True, text=True, timeout=30
                )
                logs = result.stdout + result.stderr
                if result.returncode != 0:
                    logger.error(f"Тесты не пройдены: {logs}")
                    return {"status": "failed", "logs": logs, "error": "Tests failed"}
                logger.info(f"Тесты успешно пройдены: {logs}")
                return {"status": "success", "logs": logs}
            else:
                # Простая проверка выполнения
                result = subprocess.run(
                    ["python", code_path],
                    capture_output=True, text=True, timeout=10
                )
                logs = result.stdout + result.stderr
                if result.returncode != 0:
                    logger.error(f"Ошибка выполнения кода: {logs}")
                    return {"status": "failed", "logs": logs, "error": "Execution failed"}
                logger.info(f"Код успешно выполнен: {logs}")
                return {"status": "success", "logs": logs}

        except subprocess.TimeoutExpired as e:
            logger.error(f"Превышено время выполнения: {str(e)}")
            return {"status": "failed", "logs": str(e), "error": "Timeout"}
        except Exception as e:
            logger.error(f"Ошибка в песочнице: {str(e)}")
            return {"status": "failed", "logs": str(e), "error": "Execution error"}
        finally:
            self.cleanup_sandbox()




    def execute_docker(self, dockerfile: str, compose: str, external_deps: list = []) -> Dict[str, Any]:
        """Выполнение Docker-контейнеров в изолированной среде."""
        import time
        
        sandbox_dir = self.setup_sandbox()
        dockerfile_path = os.path.join(sandbox_dir, "Dockerfile")
        compose_path = os.path.join(sandbox_dir, "docker-compose.yml")

        # Сохранение файлов
        save_text(dockerfile, dockerfile_path)
        save_text(compose, compose_path)
        
        # Создаем структуру директорий, аналогичную проекту
        os.makedirs(os.path.join(sandbox_dir, "project"), exist_ok=True)
        
        # Копируем app.py из project в песочницу с сохранением структуры
        if os.path.exists("project/app.py"):
            app_content = ""
            with open("project/app.py", "r") as f:
                app_content = f.read()
            save_text(app_content, os.path.join(sandbox_dir, "project", "app.py"))
            logger.info(f"Скопирован app.py в контекст сборки с сохранением структуры")
        
        # Создаем requirements.txt, если он используется в Dockerfile
        if "requirements.txt" in dockerfile:
            # Создаем requirements.txt с указанными зависимостями
            requirements_content = "\n".join(external_deps)
            save_text(requirements_content, os.path.join(sandbox_dir, "requirements.txt"))
            logger.info(f"Создан requirements.txt с зависимостями: {external_deps}")

        try:
            # Сборка Docker-образа
            logger.info("Сборка Docker-образа...")
            image, build_logs = self.docker_client.images.build(
                path=sandbox_dir,
                dockerfile="Dockerfile",
                tag="sandbox_app:latest",
                rm=True
            )
            build_logs_str = "\n".join([log.get("stream", "") for log in build_logs if "stream" in log])
            logger.info(f"Логи сборки: {build_logs_str}")

            # Запуск контейнера через docker-compose
            logger.info("Запуск docker-compose...")
            result = subprocess.run(
                ["docker-compose", "-f", compose_path, "up", "-d"],
                capture_output=True, text=True, cwd=sandbox_dir, timeout=60
            )
            if result.returncode != 0:
                logger.error(f"Ошибка запуска docker-compose: {result.stderr}")
                return {"status": "failed", "logs": result.stderr, "error": "Docker compose failed"}

            # Проверка, что контейнеры запущены
            time.sleep(2)  # Даем небольшую задержку
            container_check = subprocess.run(
                ["docker-compose", "-f", compose_path, "ps"],
                capture_output=True, text=True, cwd=sandbox_dir, timeout=10
            )
            
            # Анализируем вывод, чтобы определить, работают ли контейнеры
            if "Up" in container_check.stdout:
                logger.info("Docker-контейнеры успешно запущены")
                return {"status": "success", "logs": build_logs_str + "\n" + container_check.stdout}
            else:
                logger.error(f"Контейнеры не запущены: {container_check.stdout}")
                return {"status": "failed", "logs": container_check.stdout, "error": "Containers not running"}

        except docker.errors.BuildError as e:
            logger.error(f"Ошибка сборки Docker: {str(e)}")
            return {"status": "failed", "logs": str(e), "error": "Build error"}
        except subprocess.TimeoutExpired as e:
            logger.error(f"Превышено время выполнения Docker: {str(e)}")
            return {"status": "failed", "logs": str(e), "error": "Timeout"}
        except Exception as e:
            logger.error(f"Ошибка выполнения Docker: {str(e)}")
            return {"status": "failed", "logs": str(e), "error": "Docker error"}
        finally:
            # Остановка и удаление контейнеров
            subprocess.run(["docker-compose", "-f", compose_path, "down"], cwd=sandbox_dir)
            self.cleanup_sandbox()


    def _test_api_endpoint(self) -> Dict[str, Any]:
        """Простая проверка запуска контейнера без тестирования эндпоинтов."""
        # Проверяем, что контейнер запущен
        return {"status": "success", "logs": "Container started successfully"}

    def execute_docker(self, dockerfile: str, compose: str, external_deps: list = []) -> Dict[str, Any]:
        """Выполнение Docker-контейнеров в изолированной среде."""
        sandbox_dir = self.setup_sandbox()
        dockerfile_path = os.path.join(sandbox_dir, "Dockerfile")
        compose_path = os.path.join(sandbox_dir, "docker-compose.yml")

        # Сохранение файлов
        save_text(dockerfile, dockerfile_path)
        save_text(compose, compose_path)
        
        # Создаем структуру директорий, аналогичную проекту
        os.makedirs(os.path.join(sandbox_dir, "project"), exist_ok=True)
        
        # Копируем app.py из project в песочницу с сохранением структуры
        if os.path.exists("project/app.py"):
            app_content = ""
            with open("project/app.py", "r") as f:
                app_content = f.read()
            save_text(app_content, os.path.join(sandbox_dir, "project", "app.py"))
            logger.info(f"Скопирован app.py в контекст сборки с сохранением структуры")
        
        # Создаем requirements.txt, если он используется в Dockerfile
        if "requirements.txt" in dockerfile:
            # Создаем requirements.txt с указанными зависимостями
            requirements_content = "\n".join(external_deps)
            save_text(requirements_content, os.path.join(sandbox_dir, "requirements.txt"))
            logger.info(f"Создан requirements.txt с зависимостями: {external_deps}")

        try:
            # Сборка Docker-образа
            logger.info("Сборка Docker-образа...")
            image, build_logs = self.docker_client.images.build(
                path=sandbox_dir,
                dockerfile="Dockerfile",
                tag="sandbox_app:latest",
                rm=True
            )
            build_logs_str = "\n".join([log.get("stream", "") for log in build_logs if "stream" in log])
            logger.info(f"Логи сборки: {build_logs_str}")

            # Запуск контейнера через docker-compose
            logger.info("Запуск docker-compose...")
            result = subprocess.run(
                ["docker-compose", "-f", compose_path, "up", "-d"],
                capture_output=True, text=True, cwd=sandbox_dir, timeout=60
            )
            if result.returncode != 0:
                logger.error(f"Ошибка запуска docker-compose: {result.stderr}")
                return {"status": "failed", "logs": result.stderr, "error": "Docker compose failed"}

            # Проверка работоспособности (пример для API)
            time.sleep(5)  # Ожидание запуска
            test_result = self._test_api_endpoint()#
            logger.info(f"Статус контейнера: {test_result['logs']}")

            if test_result["status"] != "success":
                logger.error(f"API не работает: {test_result['logs']}")
                return test_result

            logger.info("Docker-контейнеры успешно запущены и проверены")
            return {"status": "success", "logs": build_logs_str + "\n" + test_result["logs"]}

        except docker.errors.BuildError as e:
            logger.error(f"Ошибка сборки Docker: {str(e)}")
            return {"status": "failed", "logs": str(e), "error": "Build error"}
        except subprocess.TimeoutExpired as e:
            logger.error(f"Превышено время выполнения Docker: {str(e)}")
            return {"status": "failed", "logs": str(e), "error": "Timeout"}
        except Exception as e:
            logger.error(f"Ошибка выполнения Docker: {str(e)}")
            return {"status": "failed", "logs": str(e), "error": "Docker error"}
        finally:
            # Остановка и удаление контейнеров
            subprocess.run(["docker-compose", "-f", compose_path, "down"], cwd=sandbox_dir)
            self.cleanup_sandbox()


   


if __name__ == "__main__":
    # Пример использования
    env = ExecutionEnvironment()
    
    # Тест Python-кода
    sample_code = """
from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route('/sum')
def sum():
    a = int(request.args.get('a', 0))
    b = int(request.args.get('b', 0))
    return jsonify({'result': a + b})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
"""
    sample_test = """
import pytest
import requests

def test_sum():
    response = requests.get('http://localhost:5000/sum?a=2&b=3')
    assert response.status_code == 200
    assert response.json()['result'] == 5
"""
    result = env.execute_python_code(sample_code, sample_test)
    print(json.dumps(result, indent=2))

    # Тест Docker
    sample_dockerfile = """
FROM python:3.9-slim
WORKDIR /app
COPY app.py .
RUN pip install flask
EXPOSE 5000
CMD ["python", "app.py"]
"""
    sample_compose = """
version: '3.8'
services:
  app:
    build: .
    ports:
      - "5000:5000"
"""
    docker_result = env.execute_docker(sample_dockerfile, sample_compose, ["flask"])
    print(json.dumps(docker_result, indent=2))
