from aiohttp import web
import json

async def sum_handler(request):
    try:
        # Извлечение параметров a и b из GET-запроса
        a = request.query.get('a')
        b = request.query.get('b')

        # Валидация входных данных
        if a is None or b is None:
            return web.json_response({'error': 'Параметры a и b обязательны.'}, status=400)

        try:
            a = float(a)
            b = float(b)
        except ValueError:
            return web.json_response({'error': 'Параметры a и b должны быть числами.'}, status=400)

        # Вычисление суммы
        result = a + b

        # Формирование ответа
        response_data = {
            'result': result,
            'status': 'success'
        }
        return web.json_response(response_data)

    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

async def init_app():
    app = web.Application()
    app.router.add_get('/sum', sum_handler)
    return app

if __name__ == '__main__':
    web.run_app(init_app(), port=8080)