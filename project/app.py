import argparse
import collections
import re

def validate_file_path(file_path):
    """Validate if the file path is a valid string."""
    if not isinstance(file_path, str) or not file_path.strip():
        raise ValueError("Invalid file path. It must be a non-empty string.")

def read_file(file_path):
    """Read the content of the file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"The file '{file_path}' was not found.")
    except IOError:
        raise IOError(f"An error occurred while reading the file '{file_path}'.")

def analyze_text(text):
    """Analyze the text and return the required metrics."""
    total_characters = len(text)
    lines = text.splitlines()
    total_lines = len(lines)
    
    words = re.findall(r'\b\w+\b', text.lower())
    total_words = len(words)
    
    word_counter = collections.Counter(words)
    most_common_words = word_counter.most_common(10)
    
    average_word_length = sum(len(word) for word in words) / total_words if total_words > 0 else 0
    longest_sentence = max(re.split(r'[.!?]+', text), key=len, default="")
    
    return {
        "total_characters": total_characters,
        "total_words": total_words,
        "total_lines": total_lines,
        "most_common_words": most_common_words,
        "average_word_length": average_word_length,
        "longest_sentence": longest_sentence.strip()
    }

def main(input_file):
    """Main function to analyze the text file."""
    validate_file_path(input_file)
    text = read_file(input_file)
    analysis_result = analyze_text(text)
    
    print(analysis_result)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze a text file.")
    parser.add_argument("input_file", type=str, help="Path to the input text file.")
    
    args = parser.parse_args()
    main(args.input_file)