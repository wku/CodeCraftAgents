import argparse
import collections
import re
import os

def validate_file(input_file):
    """Проверяет, существует ли файл и является ли он текстовым."""
    if not os.path.isfile(input_file):
        raise FileNotFoundError(f"Файл '{input_file}' не найден.")
    if not input_file.endswith('.txt'):
        raise ValueError("Файл должен быть текстовым (.txt).")

def text_analyzer(input_file):
    """Анализирует текстовый файл и возвращает статистику."""
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
                if sentence.strip():  # Проверка на пустую строку
                    if len(sentence) > len(longest_sentence):
                        longest_sentence = sentence.strip()
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
        results = text_analyzer(args.input_file)
        print("Результаты анализа:")
        print(f"Общее количество символов: {results['total_characters']}")
        print(f"Общее количество слов: {results['total_words']}")
        print(f"Общее количество строк: {results['total_lines']}")
        print(f"10 наиболее часто встречающихся слов: {results['most_common_words']}")
        print(f"Средняя длина слова: {results['average_word_length']:.2f}")
        print(f"Самое длинное предложение: {results['longest_sentence']}")
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    main()