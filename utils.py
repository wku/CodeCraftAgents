# utils.py
import os
import json
import logging
import yaml
from typing import Any, List, Optional  # Dict заменён на dict в коде
from typing import Any, List, Optional
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("project/system.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "multi_agent_system"
VECTOR_SIZE = 384  # Для all-MiniLM-L6-v2
MODEL = "openai/gpt-4o-mini"

# Клиенты
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)
qdrant_client = QdrantClient(QDRANT_HOST, port=QDRANT_PORT)
model = SentenceTransformer('all-MiniLM-L6-v2')






def load_yaml(filepath: str) -> Optional[Any]:
    """Чтение YAML-файла с обработкой ошибок."""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                logger.debug(f"Загружен YAML из {filepath}")
                return data
        logger.warning(f"Файл {filepath} не найден")
        return None
    except Exception as e:
        logger.error(f"Ошибка загрузки YAML из {filepath}: {str(e)}")
        return None

def save_yaml(data: Any, filepath: str) -> None:
    """Сохранение данных в YAML-файл с проверкой пути."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        logger.info(f"Сохранён YAML в {filepath}")
    except Exception as e:
        logger.error(f"Ошибка сохранения YAML в {filepath}: {str(e)}")


def call_openrouter(prompt: str, model: str = MODEL) -> str:
    """Вызов OpenRouter API с обработкой ошибок."""
    try:
        logger.info(f"Запрос к OpenRouter, модель: {model}")
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "http://localhost",
                "X-Title": "Multi-Agent System",
            },
            model=model,
            temperature=0.15,
            messages=[{"role": "user", "content": prompt}],
            timeout=30
        )
        result = completion.choices[0].message.content
        logger.debug(f"Ответ OpenRouter: {result}")
        return result
    except Exception as e:
        logger.error(f"Ошибка OpenRouter: {str(e)}")
        return ""

def save_json(data: Any, filepath: str) -> None:
    """Сохранение данных в JSON-файл с проверкой пути."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Сохранён JSON в {filepath}")
    except Exception as e:
        logger.error(f"Ошибка сохранения JSON в {filepath}: {str(e)}")

def load_json(filepath: str) -> Optional[Any]:
    """Чтение JSON-файла с обработкой ошибок."""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.debug(f"Загружен JSON из {filepath}")
                return data
        logger.warning(f"Файл {filepath} не найден")
        return None
    except Exception as e:
        logger.error(f"Ошибка загрузки JSON из {filepath}: {str(e)}")
        return None

def save_text(text: str, filepath: str) -> None:
    """Сохранение текста в файл."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)
        logger.info(f"Сохранён текст в {filepath}, длина: {len(text)} символов")
    except Exception as e:
        logger.error(f"Ошибка сохранения текста в {filepath}: {str(e)}")

def setup_qdrant_collection() -> None:
    """Создание коллекции в Qdrant."""
    try:
        collections = qdrant_client.get_collections().collections
        if COLLECTION_NAME not in [c.name for c in collections]:
            qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
            logger.info(f"Создана коллекция {COLLECTION_NAME}")
        else:
            logger.debug(f"Коллекция {COLLECTION_NAME} уже существует")
    except Exception as e:
        logger.error(f"Ошибка создания коллекции Qdrant: {str(e)}")

def add_to_qdrant(category: str, data: Any, point_id: int) -> None:
    """Добавление данных в Qdrant с обработкой типов."""
    try:
        if not isinstance(data, str):
            data = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
        vector = model.encode(data).tolist()
        point = PointStruct(
            id=point_id,
            vector=vector,
            payload={"category": category, "content": data}
        )
        qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=[point]
        )
        logger.info(f"Добавлено в Qdrant: {category} (point_id: {point_id})")
    except Exception as e:
        logger.error(f"Ошибка добавления в Qdrant: {str(e)}, category={category}, point_id={point_id}")

def get_from_qdrant(query: str, top_k: int = 3) -> List[dict[str, Any]]:
    """Получение релевантного контекста из Qdrant."""
    try:
        query_vector = model.encode(query).tolist()
        search_result = qdrant_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=top_k
        )
        result = [{"content": r.payload["content"], "category": r.payload["category"]} for r in search_result]
        logger.debug(f"Получено из Qdrant: {len(result)} записей")
        return result
    except Exception as e:
        logger.error(f"Ошибка запроса к Qdrant: {str(e)}")
        return []

def validate_json(data: str) -> Optional[dict[str, Any]]:
    """Проверка и парсинг JSON-строки."""
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        logger.error(f"Невалидный JSON: {data}, ошибка: {str(e)}")
        return None

if __name__ == "__main__":
    # Тест функциональности
    setup_qdrant_collection()
    add_to_qdrant("test", {"key": "value"}, 1)
    result = get_from_qdrant("test")
    print(json.dumps(result, indent=2))
    save_json({"test": "data"}, "project/test.json")
    loaded = load_json("project/test.json")
    print(loaded)
    save_text("Hello, world!", "project/test.txt")
