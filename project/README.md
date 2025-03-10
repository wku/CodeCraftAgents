# README.md

## Описание
Данный проект представляет собой простой API-сервер, реализующий функциональность для вычисления суммы двух чисел. Сервер принимает два параметра через HTTP GET запрос и возвращает результат их сложения в формате JSON. 

## Установка
Для установки необходимых зависимостей выполните следующую команду:

```bash
pip install aiohttp
```

## Использование
Для запуска сервера выполните следующий скрипт:

```python
from aiohttp import web
import json

async def sum_handler(request):
    try:
        # Извлечение параметров из запроса
        a = request.query.get('a')
        b = request.query.get('b')

        # Валидация входных данных
        if a is None or b is None:
            return web.json_response({
                'status': 'error',
                'message': 'Параметры a и b обязательны.'
            }, status=400)

        try:
            a = float(a)
            b = float(b)
        except ValueError:
            return web.json_response({
                'status': 'error',
                'message': 'Параметры a и b должны быть числами (int или float).'
            }, status=400)

        # Вычисление суммы
        result = a + b

        # Формирование ответа
        return web.json_response({
            'result': result,
            'status': 'success'
        })

    except Exception as e:
        return web.json_response({
            'status': 'error',
            'message': str(e)
        }, status=500)

app = web.Application()
app.router.add_get('/sum', sum_handler)

if __name__ == '__main__':
    web.run_app(app, port=8080)
```

Сервер будет доступен по адресу `http://localhost:8080`.

## API
### Конечная точка: `/sum`
- **Метод:** GET
- **Параметры:**
  - `a` (обязательный): число (int или float), первое слагаемое.
  - `b` (обязательный): число (int или float), второе слагаемое.

#### Формат ответа
- **Успешный ответ:**
  - `result`: число (int или float), результат сложения.
  - `status`: строка, статус запроса (например, 'success').

- **Ошибка:**
  - `status`: строка, статус запроса (например, 'error').
  - `message`: строка, описание ошибки.

## Примеры
### Пример запроса
```http
GET http://localhost:8080/sum?a=5&b=10
```

### Пример успешного ответа
```json
{
    "result": 15,
    "status": "success"
}
```

### Пример запроса с ошибкой (отсутствует параметр)
```http
GET http://localhost:8080/sum?a=5
```

### Пример ответа с ошибкой
```json
{
    "status": "error",
    "message": "Параметры a и b обязательны."
}
```

### Пример запроса с ошибкой (нечисловые параметры)
```http
GET http://localhost:8080/sum?a=abc&b=10
```

### Пример ответа с ошибкой
```json
{
    "status": "error",
    "message": "Параметры a и b должны быть числами (int или float)."
}
```

## Требования
- Python 3.6 или выше
- aiohttp 3.0 или выше