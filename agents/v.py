import ast

def analyze_arguments(code: str) -> dict:
    tree = ast.parse(code)
    requires_args = False
    args = []
    requires_input_file = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'add_argument':
            if isinstance(node.func.value, ast.Name) and node.func.value.id == 'parser':
                requires_args = True
                # Проверяем, является ли аргумент позиционным (нет "--" или "-")
                if node.args and isinstance(node.args[0], ast.Str):
                    arg_name = node.args[0].s
                    if not arg_name.startswith('-'):
                        args.append(arg_name)
                        if 'file' in arg_name.lower():
                            requires_input_file = True

    return {
        "requires_args": requires_args,
        "args": args,
        "requires_input_file": requires_input_file,
        "input_file_content": "" if not requires_input_file else "dummy content"
    }


code ="""
import argparse
import collections
import re
import os

def validate_file(input_file):
    if not os.path.isfile(input_file):
        raise FileNotFoundError(f"Файл '{input_file}' не найден.")
    if not input_file.endswith('.txt'):
        raise ValueError("Файл должен быть текстовым (.txt).")

def text_analyzer(input_file):
    validate_file(input_file)

    total_characters = 0
    total_words = 0
    total_lines = 0
    word_counter = collections.Counter()
    longest_sentence = ""
    
    with open(input_file, 'r', encoding='utf-8') as file:
        for line in file:
            total_lines += 1
            total_characters += len(line)
            sentences = re.split(r'[.!?]', line)
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence:
                    if len(sentence) > len(longest_sentence):
                        longest_sentence = sentence
                    words = re.findall(r'\b\w+\b', sentence.lower())
                    total_words += len(words)
                    word_counter.update(words)

    most_common_words = word_counter.most_common(10)
    average_word_length = (total_characters / total_words) if total_words > 0 else 0

    return {
        "total_characters": total_characters,
        "total_words": total_words,
        "total_lines": total_lines,
        "most_common_words": most_common_words,
        "average_word_length": average_word_length,
        "longest_sentence": longest_sentence
    }

def main():
    parser = argparse.ArgumentParser(description="Анализатор текстового файла.")
    parser.add_argument("input_file", type=str, help="Путь к текстовому файлу для анализа.")
    
    args = parser.parse_args()
    
    try:
        result = text_analyzer(args.input_file)
        print(result)
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    main()
"""

d = analyze_arguments(code)

print(d)