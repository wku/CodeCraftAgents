import ast
import sys
import json

def analyze_arguments(code: str) -> dict:
    """
    Анализирует аргументы командной строки в Python-скрипте через статический анализ AST.
    
    Args:
        code (str): Исходный код Python-скрипта для анализа
        
    Returns:
        dict: Словарь с результатами анализа
    """
    tree = ast.parse(code)
    requires_args = False
    
    # Словари для хранения разных типов аргументов
    positional_args = []
    optional_args = []
    flag_args = []
    
    # Дополнительная информация
    requires_input_file = False
    input_file_args = []
    output_file_args = []
    imports = set()
    
    # Анализ импортов
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                imports.add(name.name)
        elif isinstance(node, ast.ImportFrom):
            imports.add(f"{node.module}")
    
    # Анализ аргументов
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'add_argument':
            if isinstance(node.func.value, ast.Name) and node.func.value.id == 'parser':
                requires_args = True
                
                # Извлекаем имя аргумента и его параметры
                arg_name = ""
                arg_help = ""
                arg_type = None
                arg_default = None
                arg_required = False
                
                # Получаем имя аргумента
                if node.args and isinstance(node.args[0], ast.Str):
                    arg_name = node.args[0].s
                
                # Анализируем ключевые параметры
                for keyword in node.keywords:
                    if keyword.arg == 'help' and isinstance(keyword.value, ast.Str):
                        arg_help = keyword.value.s
                    elif keyword.arg == 'type' and isinstance(keyword.value, ast.Name):
                        arg_type = keyword.value.id
                    elif keyword.arg == 'default':
                        if isinstance(keyword.value, ast.Str):
                            arg_default = keyword.value.s
                        elif isinstance(keyword.value, ast.Num):
                            arg_default = keyword.value.n
                        elif isinstance(keyword.value, (ast.List, ast.Tuple)):
                            arg_default = "list/tuple"
                        elif isinstance(keyword.value, ast.NameConstant):
                            arg_default = str(keyword.value.value)
                    elif keyword.arg == 'required' and isinstance(keyword.value, ast.NameConstant):
                        arg_required = keyword.value.value
                
                # Определяем тип аргумента
                if arg_name.startswith('--'):
                    # Опциональный аргумент с длинным именем
                    optional_args.append({
                        "name": arg_name,
                        "help": arg_help,
                        "type": arg_type,
                        "default": arg_default,
                        "required": arg_required
                    })
                elif arg_name.startswith('-'):
                    # Флаг
                    flag_args.append({
                        "name": arg_name,
                        "help": arg_help,
                        "default": arg_default
                    })
                else:
                    # Позиционный аргумент
                    positional_args.append({
                        "name": arg_name,
                        "help": arg_help,
                        "type": arg_type
                    })
                
                # Проверяем, связан ли аргумент с файлами
                if 'file' in arg_name.lower() or 'path' in arg_name.lower():
                    if 'input' in arg_name.lower() or 'in' in arg_name.lower() or 'src' in arg_name.lower():
                        requires_input_file = True
                        input_file_args.append(arg_name)
                    elif 'output' in arg_name.lower() or 'out' in arg_name.lower() or 'dst' in arg_name.lower():
                        output_file_args.append(arg_name)
    
    # Генерируем пример команды запуска
    example_command = "python script.py"
    for arg in positional_args:
        example_command += f" <{arg['name']}>"
    
    for arg in optional_args:
        if arg['required']:
            example_command += f" {arg['name']} <value>"
        else:
            example_command += f" [{arg['name']} <value>]"
    
    for arg in flag_args:
        example_command += f" [{arg['name']}]"
    
    # Определяем обязательные библиотеки
    dependencies = ["argparse"]
    for imp in imports:
        if imp not in ["sys", "os", "argparse", "__future__"]:
            dependencies.append(imp)
    
    return {
        "requires_args": requires_args,
        "positional_args": positional_args,
        "optional_args": optional_args,
        "flag_args": flag_args,
        "requires_input_file": requires_input_file,
        "input_file_args": input_file_args,
        "output_file_args": output_file_args,
        "dependencies": dependencies,
        "imports": list(imports),
        "example_command": example_command,
        "input_file_content": "" if not requires_input_file else "dummy content"
    }

def print_analysis_report(result):
    """
    Выводит отчет об анализе в удобочитаемом формате.
    
    Args:
        result (dict): Результат анализа функции analyze_arguments
    """
    print("\n=== ОТЧЕТ ОБ АНАЛИЗЕ АРГУМЕНТОВ КОМАНДНОЙ СТРОКИ ===\n")
    
    print(f"Требуются аргументы: {'Да' if result['requires_args'] else 'Нет'}\n")
    
    if result['positional_args']:
        print("ПОЗИЦИОННЫЕ АРГУМЕНТЫ:")
        for arg in result['positional_args']:
            print(f"  • {arg['name']}")
            if arg['help']:
                print(f"    Описание: {arg['help']}")
            if arg['type']:
                print(f"    Тип: {arg['type']}")
            print()
    
    if result['optional_args']:
        print("ОПЦИОНАЛЬНЫЕ АРГУМЕНТЫ:")
        for arg in result['optional_args']:
            req_str = " (обязательный)" if arg['required'] else ""
            print(f"  • {arg['name']}{req_str}")
            if arg['help']:
                print(f"    Описание: {arg['help']}")
            if arg['type']:
                print(f"    Тип: {arg['type']}")
            if arg['default'] is not None:
                print(f"    Значение по умолчанию: {arg['default']}")
            print()
    
    if result['flag_args']:
        print("ФЛАГИ:")
        for arg in result['flag_args']:
            print(f"  • {arg['name']}")
            if arg['help']:
                print(f"    Описание: {arg['help']}")
            if arg['default'] is not None:
                print(f"    Значение по умолчанию: {arg['default']}")
            print()
    
    print(f"Требуется входной файл: {'Да' if result['requires_input_file'] else 'Нет'}")
    if result['input_file_args']:
        print(f"  Аргументы входных файлов: {', '.join(result['input_file_args'])}")
    
    if result['output_file_args']:
        print(f"  Аргументы выходных файлов: {', '.join(result['output_file_args'])}")
    
    print("\nЗАВИСИМОСТИ:")
    for dep in result['dependencies']:
        print(f"  • {dep}")
    
    print("\nИМПОРТЫ:")
    for imp in result['imports']:
        print(f"  • {imp}")
    
    print(f"\nПРИМЕР ИСПОЛЬЗОВАНИЯ:\n  {result['example_command']}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python script_analyzer.py <путь_к_файлу>")
        sys.exit(1)
    
    try:
        with open(sys.argv[1], 'r') as file:
            code = file.read()
        
        result = analyze_arguments(code)
        print_analysis_report(result)
        
        # Также сохраняем результаты в JSON
        output_file = sys.argv[1] + "_analysis.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\nПодробные результаты анализа сохранены в {output_file}")
    
    except FileNotFoundError:
        print(f"Ошибка: Файл {sys.argv[1]} не найден")
        sys.exit(1)
    except SyntaxError as e:
        print(f"Ошибка синтаксиса в анализируемом файле: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        sys.exit(1)
