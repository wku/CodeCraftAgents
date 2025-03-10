from aiohttp import web
import json

async def sum_handler(request):
    try:
        # Извлечение параметров a и b из запроса
        a = request.query.get('a')
        b = request.query.get('b')

        # Валидация входных данных
        if a is None or b is None:
            raise ValueError("Параметры 'a' и 'b' обязательны.")
        
        # Преобразование параметров в числа
        a = float(a)
        b = float(b)

        # Вычисление суммы
        result = a + b

        # Формирование ответа
        return web.json_response({'result': result})

    except ValueError as ve:
        return web.json_response({'error': str(ve)}, status=400)
    except Exception as e:
        return web.json_response({'error': 'Произошла ошибка: ' + str(e)}, status=500)

async def init_app():
    app = web.Application()
    app.router.add_get('/sum', sum_handler)
    return app

if __name__ == '__main__':
    web.run_app(init_app(), port=8080)