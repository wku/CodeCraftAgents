# main.py
import os
import json
import time
import shutil
from feedback_loop import FeedbackLoop
from execution_env import ExecutionEnvironment
from utils import logger, save_json, load_json, save_text, save_yaml
import shutil
import os


def initialize_config_files():
    """Инициализация конфигурационных файлов."""
    os.makedirs("project", exist_ok=True)
    
    # Проверка и использование settings.yml
    settings_path = "settings.yml"
    if not os.path.exists(settings_path):
        # Создание файла settings.yml с дефолтными настройками
        default_settings = {
            'feedback': {
                "max_iterations": 3,
                "confidence_threshold": 0.7,
                "retry_delay": 2,
                "fallback_agent": "decomposer",
                "agent_specific": {
                    "decomposer": {"max_iterations": 5, "confidence_threshold": 0.8},
                    "validator": {"max_iterations": 4, "confidence_threshold": 0.75},
                    "codegen": {"max_iterations": 3, "confidence_threshold": 0.85},
                    "docker": {"max_iterations": 2, "confidence_threshold": 0.9}
                }
            },
            'verification_rules': {
                "decomposer": {
                    "required_fields": ["modules"],
                    "module_fields": ["name", "input", "output", "logic", "external"],
                    "error_patterns": ["предположение", "неизвестно", "не указано"],
                    "success_criteria": "all fields present and no assumptions in logic",
                    "priority": 1
                },
                "validator": {
                    "required_fields": ["status"],
                    "valid_statuses": ["approved", "rejected"],
                    "error_patterns": ["непонятно", "ошибка"],
                    "success_criteria": "status is 'approved' or 'rejected' with comments",
                    "priority": 2
                },
                "consistency": {
                    "required_fields": ["status"],
                    "valid_statuses": ["approved", "rejected"],
                    "error_patterns": ["противоречие", "несоответствие"],
                    "success_criteria": "status is 'approved' or 'rejected' with inconsistencies",
                    "priority": 3
                },
                "codegen": {
                    "required_fields": None,
                    "error_patterns": ["syntax error", "import error", "undefined"],
                    "success_criteria": "valid Python syntax and dependencies included",
                    "priority": 4
                },
                "extractor": {
                    "required_fields": ["file_path"],
                    "error_patterns": ["not found", "invalid path"],
                    "success_criteria": "file_path exists and contains valid code",
                    "priority": 5
                },
                "docker": {
                    "required_fields": ["dockerfile", "compose"],
                    "error_patterns": ["build failed", "invalid dockerfile"],
                    "success_criteria": "Dockerfile and docker-compose.yml are valid and buildable",
                    "priority": 6
                },
                "monitor": {
                    "required_fields": ["command"],
                    "valid_commands": ["none", "Перезапустить <agent>", "Принудительный переход к consistency"],
                    "error_patterns": ["invalid command"],
                    "success_criteria": "valid command based on state",
                    "priority": 9
                },
                "knowledge": {
                    "required_fields": None,
                    "error_patterns": ["empty", "no data"],
                    "success_criteria": "non-empty list of categorized data",
                    "priority": 7
                },
                "coordinator": {
                    "required_fields": None,
                    "error_patterns": ["unknown agent", "invalid transition"],
                    "success_criteria": "returns a valid agent name",
                    "priority": 8
                },
                "tester": {
                    "required_fields": ["tests"],
                    "error_patterns": ["pytest error", "test failed"],
                    "success_criteria": "valid pytest code covering key functionality",
                    "priority": 10
                },
                "docs": {
                    "required_fields": None,
                    "error_patterns": ["missing usage", "no documentation"],
                    "success_criteria": "README.md contains interfaces and usage instructions",
                    "priority": 11
                }
            }
        }
        save_yaml(default_settings, settings_path)
        logger.info(f"Создан файл {settings_path} с настройками по умолчанию")


def save_code_safely(code, file_path):
    """Безопасное сохранение кода с проверкой типа данных."""
    try:
        logger.info (f"save_code_safely вызвана с типом code: {type (code)}")

        # Если code - словарь с ключом "data"
        if isinstance (code, dict) and "data" in code:
            logger.info (f"save_code_safely: code является словарем с ключом 'data', тип data: {type (code['data'])}")

            # Если code["data"] - строка, сохраняем напрямую
            if isinstance (code["data"], str):
                logger.info (f"save_code_safely 1 isinstance code.keys(): {code.keys ()}")
                save_text (code["data"], file_path)
                return True
            # Если code["data"] - словарь
            elif isinstance (code["data"], dict):
                logger.info (f"save_code_safely: code['data'] является словарем с ключами: {code['data'].keys ()}")

                # Обработка вложенной структуры, возвращаемой CodeGeneratorAgent
                if "code" in code["data"]:
                    logger.info (f"save_code_safely: найден 'code' внутри code['data']")
                    save_text (code["data"]["code"], file_path)
                    return True
                # Проверка на наличие ошибки
                elif "error" in code["data"]:
                    logger.error (f"save_code_safely Обнаружена ошибка в данных: {code['data']['error']}")
                    return False
                else:
                    logger.error (f"save_code_safely: В code['data'] нет ключа 'code' или 'error'")
                    return False
            else:
                logger.error (f"save_code_safely Ошибка сохранения кода: code['data'] не является строкой или словарем, тип: {type (code['data'])}")
                return False

        # Если code - это словарь с ключом "code" напрямую
        elif isinstance (code, dict) and "code" in code:
            logger.info (f"save_code_safely 3 isinstance code.keys(): {code.keys ()}")
            # Прямая обработка, если код находится в ключе "code"
            content = code["code"]

            # Проверка типа содержимого code
            if isinstance (content, str):
                save_text (content, file_path)
                return True
            elif isinstance (content, dict) and "code" in content:
                # Вложенная структура внутри "code"
                save_text (content["code"], file_path)
                return True
            else:
                # Преобразуем к строке, если не строка
                logger.warning (f"save_code_safely: содержимое 'code' не является строкой, преобразуем к строке")
                try:
                    # Если значение 'code' это не строка, попробуем получить только содержимое кода
                    # Ищем строку, которая выглядит как код Python
                    if isinstance (content, dict) and any (k in content for k in ["code", "data"]):
                        for key in ["code", "data"]:
                            if key in content and isinstance (content[key], str):
                                save_text (content[key], file_path)
                                logger.info (f"save_code_safely: извлечен код из вложенной структуры по ключу {key}")
                                return True

                    # Если не нашли подходящий ключ, сохраняем как строку
                    code_str = str (content)
                    # Если значение выглядит как словарь в строке, попробуем распарсить его
                    if code_str.startswith ("{") and code_str.endswith ("}"):
                        try:
                            code_dict = eval (code_str)  # Осторожно с eval!
                            if isinstance (code_dict, dict) and "code" in code_dict:
                                save_text (code_dict["code"], file_path)
                                logger.info (f"save_code_safely: извлечен код из строкового представления словаря")
                                return True
                        except:
                            pass

                    # Если не удалось распарсить, сохраняем как есть
                    save_text (code_str, file_path)
                    return True
                except Exception as inner_e:
                    logger.error (f"save_code_safely: ошибка при попытке обработать нестроковое значение 'code': {str (inner_e)}")
                    return False

        # Если code - строка, сохраняем напрямую
        elif isinstance (code, str):
            if code.startswith ("{") and ("code" in code or "data" in code):
                logger.info (f"save_code_safely: code выглядит как строка с JSON, пробуем распарсить")
                try:
                    # Проверяем, может это строка с JSON, которую нужно распарсить
                    import json
                    code_json = json.loads (code)

                    if isinstance (code_json, dict):
                        if "code" in code_json:
                            save_text (code_json["code"], file_path)
                            logger.info (f"save_code_safely: извлечен код из JSON строки по ключу 'code'")
                            return True
                        elif "data" in code_json and isinstance (code_json["data"], str):
                            save_text (code_json["data"], file_path)
                            logger.info (f"save_code_safely: извлечен код из JSON строки по ключу 'data'")
                            return True
                except:
                    # Если не получилось распарсить как JSON, сохраняем как обычную строку
                    pass

            logger.info (f"save_code_safely 2: сохранение строки напрямую")
            save_text (code, file_path)
            return True

        else:
            logger.error (f"save_code_safely Ошибка сохранения кода: code не является строкой или словарем с 'data' или 'code', тип: {type (code)}")
            # Последняя попытка - преобразовать к строке
            try:
                code_str = str (code)
                logger.warning (f"save_code_safely: попытка сохранить код, преобразованный к строке")
                save_text (code_str, file_path)
                return True
            except:
                return False
    except Exception as e:
        logger.error (f"save_code_safely Исключение при сохранении кода в {file_path}: {str (e)}")
        return False


def is_valid_result(result):
    """Проверка валидности результата агента."""
    if result is None:
        return False
    
    if isinstance(result, dict) and "error" in result:
        return False
    
    return True


def handle_docker_setup(state, feedback_loop, execution_env, max_retries=3):
    """Специальная обработка для настройки Docker."""
    from utils import call_openrouter

    # Проверяем наличие файла app.py
    if not os.path.exists("project/app.py"):
        # Получаем код из предыдущего шага codegen
        code_data = state["previous_results"].get("codegen")
        if code_data:
            # Сохраняем код в app.py
            if save_code_safely(code_data, "project/app.py"):
                logger.info("Восстановлен файл app.py из результатов codegen")
            else:
                logger.error("Не удалось восстановить app.py из результатов codegen")
                return False
        else:
            logger.error("Отсутствуют результаты codegen и файл app.py")
            return False
    
    # Получаем зависимости из плана декомпозиции
    external_deps = []
    decomposer_result = state["previous_results"].get("decomposer")
    if decomposer_result and isinstance(decomposer_result, dict) and "data" in decomposer_result:
        modules = decomposer_result["data"].get("modules", [])
        if modules and isinstance(modules, list) and len(modules) > 0:
            external_deps = modules[0].get("external", [])
    
    # Запускаем Docker с проверкой ошибок
    for attempt in range(max_retries):
        result = feedback_loop.run_agent_with_feedback(
            "docker",
            {"file_path": "project/app.py", "external": external_deps},
            state["task"],
            state
        )
        
        # Проверяем успешность выполнения
        if "error" not in result:
            # Используем LLM для извлечения Dockerfile и docker-compose из результата
            prompt = f"""
Извлеки Dockerfile и docker-compose.yml из следующего результата:

{json.dumps(result, indent=2)}

Верни JSON в формате:
{{
  "dockerfile": "<содержимое Dockerfile>",
  "compose": "<содержимое docker-compose.yml>"
}}

Не добавляй никаких комментариев, только JSON.
"""
            try:
                llm_response = call_openrouter(prompt)
                parsed_result = json.loads(llm_response)
                
                dockerfile = parsed_result.get("dockerfile", "")
                compose = parsed_result.get("compose", "")
                
                if not dockerfile or not compose:
                    logger.warning(f"LLM не смог извлечь Dockerfile или docker-compose, пробуем другой подход")
                    
                    # Запасной вариант извлечения
                    if isinstance(result, dict):
                        if "dockerfile" in result:
                            dockerfile = result["dockerfile"]
                        elif "data" in result and isinstance(result["data"], dict) and "dockerfile" in result["data"]:
                            dockerfile = result["data"]["dockerfile"]
                        
                        if "compose" in result:
                            compose = result["compose"]
                        elif "data" in result and isinstance(result["data"], dict) and "compose" in result["data"]:
                            compose = result["data"]["compose"]
                
                logger.info(f"Извлечено из результата: Dockerfile ({len(dockerfile)} символов), compose ({len(compose)} символов)")
                
                # Выполняем проверку Docker
                docker_verification = execution_env.execute_docker(
                    dockerfile,
                    compose,
                    external_deps
                )
                
                if docker_verification["status"] == "success":
                    state["data"] = result
                    state["previous_results"]["docker"] = result
                    return True
                    
            except json.JSONDecodeError:
                logger.error(f"Не удалось распарсить JSON из ответа LLM: {llm_response}")
            except Exception as e:
                logger.error(f"Ошибка при обработке результата Docker: {str(e)}")
        
        logger.warning(f"Попытка настройки Docker {attempt+1}/{max_retries} не удалась")
        time.sleep(2)
    
    logger.error("Все попытки настройки Docker не удались")
    return False


def clear_dir(project_dir):
    # Очистка директории проекта перед началом работы


    
    # Удаляем директорию проекта, если существует
    if os.path.exists(project_dir):
        shutil.rmtree(project_dir)
        logger.info(f"Директория {project_dir} удалена")
    
    # Создаем новую директорию
    os.makedirs(project_dir, exist_ok=True)
    logger.info(f"Создана новая директория {project_dir}")




def tackt_1(feedback_loop, task):
    # Проверка валидности входного запроса
    request_validation_result = feedback_loop.run_agent_with_feedback (
        "request_validation",
        task,
        task,
        {"task": task}
    )
    # Проверка результата валидации
    if (not isinstance (request_validation_result, dict) or
            "data" not in request_validation_result or
            not request_validation_result["data"].get ("is_valid", False)):

        # Логирование причин отклонения
        reasons = request_validation_result.get ("data", {}).get ("reasons", ["Неизвестная причина"])
        logger.error ("Входной запрос не прошел валидацию:")
        for reason in reasons:
            logger.error (f"- {reason}")
        return False, request_validation_result

    else:
        return True, request_validation_result




def main(task):

    clear_dir("project")

     # Инициализация компонентов
    feedback_loop = FeedbackLoop() # + all agents + verification.py
    execution_env = ExecutionEnvironment() # работа с кодом

    # Инициализация конфигурационных файлов
    initialize_config_files()

    result_tackt_1, request_validation_result = tackt_1 (feedback_loop, task)
    if not result_tackt_1:
        print ("Входной запрос не может быть обработан. Пожалуйста, уточните задание.")
        return


    # Инициализация состояния
    state = {
        "task": task,
        "current_agent": "decomposer",
        "data": None,
        "step": 0,
        "validator_consecutive_runs": 0,
        "verification": None,
        "max_steps": 30,  # Предотвращение бесконечных циклов / было 50
        "previous_results": {
            "request_validation": request_validation_result
        },
        "docker_retry_count": 0  # Счетчик попыток для docker
    }
    save_json(state, "project/state.json")
    




    # Ожидаемая последовательность агентов ... todo
    expected_flow = [
        "decomposer", "validator", "consistency", "codegen", "extractor", "docker", "tester", "docs"
    ]
    
    # Основной цикл выполнения
    while state["step"] < state["max_steps"]:
        state = load_json("project/state.json")
        current_agent = state["current_agent"]
        logger.info(f"Текущий шаг: {state['step']}, текущий агент: {current_agent}")

        if not current_agent:
            logger.info("Все этапы завершены успешно!")
            break
            
        # Проверка на превышение лимита попыток для docker todo
        if current_agent == "docker" and state.get("docker_retry_count", 0) > 5:
            logger.warning("Превышен лимит попыток для Docker, переход к следующему этапу")
            state["current_agent"] = "tester"
            save_json(state, "project/state.json")
            continue

        # Сначала определяем входные данные для текущего агента
        agent_input = None

        if current_agent == "decomposer":
            agent_input = state["task"]
        elif current_agent == "validator":
            if "decomposer" in state["previous_results"]:
                agent_input = state["previous_results"]["decomposer"]
            else:
                logger.error("Отсутствуют результаты decomposer для validator")
                state["current_agent"] = "decomposer"
                save_json(state, "project/state.json")
                continue
        elif current_agent == "consistency":
            if "decomposer" in state["previous_results"]:
                agent_input = state["previous_results"]["decomposer"]
            else:
                logger.error("Отсутствуют результаты decomposer для consistency")
                state["current_agent"] = "decomposer"
                save_json(state, "project/state.json")
                continue
        elif current_agent == "codegen":
            if "consistency" in state["previous_results"]:
                # Используем результаты decomposer и consistency для генерации кода
                agent_input = state["previous_results"]["decomposer"]
            else:
                logger.error("Отсутствуют результаты consistency для codegen")
                state["current_agent"] = "consistency"
                save_json(state, "project/state.json")
                continue
        elif current_agent == "extractor":
            if "codegen" in state["previous_results"]:
                agent_input = state["previous_results"]["codegen"]
            else:
                logger.error("Отсутствуют результаты codegen для extractor")
                state["current_agent"] = "codegen"
                save_json(state, "project/state.json")
                continue
        elif current_agent == "docker":
            # Специальная обработка Docker
            success = handle_docker_setup(state, feedback_loop, execution_env)
            if success:
                state["current_agent"] = "tester"
            else:
                state["docker_retry_count"] = state.get("docker_retry_count", 0) + 1
                if state["docker_retry_count"] > 5:
                    state["current_agent"] = "tester"
                    logger.warning("Пропуск Docker после множественных попыток")
            save_json(state, "project/state.json")
            continue
        elif current_agent == "tester":
            # Для тестера нужен код приложения
            if os.path.exists("project/app.py"):
                with open("project/app.py", "r") as f:
                    app_code = f.read()
                agent_input = app_code
            else:
                logger.error("Отсутствует файл app.py для tester")
                # Восстанавливаем из предыдущих результатов
                if "codegen" in state["previous_results"]:
                    code_result = state["previous_results"]["codegen"]
                    if save_code_safely(code_result, "project/app.py"):
                        agent_input = code_result
                    else:
                        # Если не удалось восстановить, возвращаемся к codegen
                        state["current_agent"] = "codegen"
                        save_json(state, "project/state.json")
                        continue
                else:
                    state["current_agent"] = "codegen"
                    save_json(state, "project/state.json")
                    continue
        elif current_agent == "docs":
            # Для документации нужен весь план и код
            doc_input = {
                "plan": state["previous_results"].get("decomposer", {}),
                "code": open("project/app.py", "r").read() if os.path.exists("project/app.py") else "# Код не доступен"
            }
            agent_input = doc_input
            
            # Отслеживаем количество попыток docs
            if "docs_retry_count" not in state:
                state["docs_retry_count"] = 0
            state["docs_retry_count"] += 1
            
            # Если это 3-я или более попытка, принудительно считаем docs успешным
            if state["docs_retry_count"] >= 3:
                logger.warning("Принудительное завершение процесса после многократных попыток документации")
                # Мы можем либо считать docs успешным...
                result = {"success": True, "message": "Документация принудительно принята"}
                state["data"] = result
                state["previous_results"]["docs"] = result
                state["current_agent"] = None  # Завершение процесса
                save_json(state, "project/state.json")
                continue



        else:
            # Для остальных агентов используем последние данные
            agent_input = state["data"] if state["data"] else state["task"]

        # Выполнение агента
        try:
            # Запуск агента с подготовленными входными данными
            result = feedback_loop.run_agent_with_feedback(
                current_agent,
                agent_input,
                state["task"],
                state
            )
            #для дебага "decomposer", "validator", "consistency", "codegen", "extractor", "docker", "tester", "docs"
            # if current_agent not in ["decomposer", "validator", "consistency"]:
            #     logger.error (f" *******************************")
            #     logger.error (f"current_agent: {current_agent}")
            #     logger.error (f"result: {json.dumps(result, indent=4, ensure_ascii=False,sort_keys=True) }")
            #     logger.error (f" *******************************")
            #     logger.error (f" agent_input: {agent_input}")
            #     logger.error (f" *******************************")
            #     logger.error (f" state: {state}")
            #
            #     return

            # Проверка результата
            if not is_valid_result(result):
                logger.error(f"Агент {current_agent} вернул невалидный результат")
                # Повторяем этот шаг или возвращаемся на предыдущий
                if current_agent == expected_flow[0]:
                    # Для decomposer просто повторяем
                    continue
                else:
                    # Для других возвращаемся на шаг назад
                    idx = expected_flow.index(current_agent)
                    state["current_agent"] = expected_flow[idx-1]
                    save_json(state, "project/state.json")
                    continue
            
            # Обработка результата в зависимости от текущего агента
            if current_agent == "codegen":
                # Сохраняем код в файл
                if not save_code_safely(result, "project/app.py"):
                    logger.error("Не удалось сохранить код в project/app.py")
                    # Повторяем генерацию кода
                    continue
                else:
                    # Проверяем код выполнением
                    execution_result = execution_env.execute_python_code(result if isinstance(result, str) else result.get("data", ""))
                    if execution_result["status"] != "success":
                        logger.warning(f"Код не прошёл проверку выполнения: {execution_result['logs']}")
                        state["data"] = {"error": "Code execution failed", "logs": execution_result['logs']}
                        continue
            elif current_agent == "extractor":
                # Проверка корректности экстракции
                file_path = result.get("file_path") if isinstance(result, dict) else None
                if file_path and not os.path.exists(file_path):
                    # Если файл не существует, пытаемся создать его
                    code_data = state["previous_results"].get("codegen")
                    if code_data and save_code_safely(code_data, file_path):
                        logger.info(f"Создан файл {file_path} из результатов codegen")
                    else:
                        logger.error(f"Не удалось создать файл {file_path}")
                        continue
            elif current_agent == "tester":
                # Запуск тестов
                code = None
                if os.path.exists("project/app.py"):
                    with open("project/app.py", "r") as f:
                        code = f.read()
                else:
                    code = state["previous_results"].get("codegen", {}).get("data", "")
                
                if code and isinstance(result, dict) and "tests" in result:
                    execution_result = execution_env.execute_python_code(code, result["tests"])
                    if execution_result["status"] != "success":
                        logger.warning(f"Тесты не пройдены: {execution_result['logs']}")
                        state["data"] = {"error": "Tests failed", "logs": execution_result['logs']}
                        continue

            # Обновление состояния
            state["data"] = result
            state["previous_results"][current_agent] = result
            state["step"] += 1

            # Определение следующего агента
            verification = state.get("verification", {"status": "passed", "confidence": 1.0, "issues": []})
            
            # Если текущий агент в ожидаемом потоке, берем следующий из списка
            if current_agent in expected_flow:
                idx = expected_flow.index(current_agent)
                if idx < len(expected_flow) - 1:
                    next_agent = expected_flow[idx + 1]
                else:
                    next_agent = None  # Завершение процесса
            else:
                # В противном случае используем FeedbackLoop для определения
                next_agent = feedback_loop.determine_next_agent(current_agent, result, verification)
            
            state["current_agent"] = next_agent
            save_json(state, "project/state.json")

        except Exception as e:
            logger.error(f"Исключение при выполнении агента {current_agent}: {str(e)}")
            # Возвращаемся к предыдущему шагу в случае исключения
            if current_agent in expected_flow:
                idx = expected_flow.index(current_agent)
                if idx > 0:
                    state["current_agent"] = expected_flow[idx - 1]
                save_json(state, "project/state.json")
            time.sleep(1)
            continue

        # Задержка между шагами
        time.sleep(1)
    
    if state["step"] >= state["max_steps"]:
        logger.warning(f"Превышено максимальное количество шагов ({state['max_steps']}), выполнение остановлено")

if __name__ == "__main__":
    # Задаем задачу
    # task = "Создать API-сервер, роут /sum, на вход два гет параметра a и b, цифры, возвращает сумму a и b. Использовать aiohttp"
    task = """

    Создайте программу на Python, которая анализирует текстовые файлы и предоставляет статистические данные о содержимом Программа должна иметь следующую функциональность:

    1. Чтение текстового файла, путь к которому указывается как аргумент командной строки
    2. Подсчет общего количества символов, слов и строк
    3. Определение 10 наиболее часто встречающихся слов
    4. Вычисление средней длины слова
    5. Поиск самого длинного предложения


    ### Требования к реализации
    * Весь код должен быть в одном файле `text_analyzer.py`
    * Реализовать парсинг аргументов командной строки


    ### Пример использования

    python text_analyzer.py --input example.txt 


    """
    main(task)
