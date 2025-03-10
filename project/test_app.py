import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from app import sum_handler
class TestSumHandler(AioHTTPTestCase):

    async def get_application(self):
        app = web.Application()
        app.router.add_get('/sum', sum_handler)
        return app


    async def test_sum_valid_numbers(self):
        response = await self.client.get('/sum?a=3&b=4')
        assert response.status == 200
        json_response = await response.json()
        assert json_response['status'] == 'success'
        assert json_response['result'] == 7


    async def test_sum_missing_parameters(self):
        response = await self.client.get('/sum?a=3')
        assert response.status == 400
        json_response = await response.json()
        assert json_response['status'] == 'error'
        assert json_response['message'] == 'Параметры a и b обязательны.'


    async def test_sum_invalid_numbers(self):
        response = await self.client.get('/sum?a=three&b=four')
        assert response.status == 400
        json_response = await response.json()
        assert json_response['status'] == 'error'
        assert json_response['message'] == 'Параметры a и b должны быть числами (int или float).'


    async def test_sum_float_numbers(self):
        response = await self.client.get('/sum?a=3.5&b=2.5')
        assert response.status == 200
        json_response = await response.json()
        assert json_response['status'] == 'success'
        assert json_response['result'] == 6.0


    async def test_sum_large_numbers(self):
        response = await self.client.get('/sum?a=1e10&b=1e10')
        assert response.status == 200
        json_response = await response.json()
        assert json_response['status'] == 'success'
        assert json_response['result'] == 2e10


    async def test_sum_negative_numbers(self):
        response = await self.client.get('/sum?a=-3&b=-4')
        assert response.status == 200
        json_response = await response.json()
        assert json_response['status'] == 'success'
        assert json_response['result'] == -7


    async def test_sum_zero(self):
        response = await self.client.get('/sum?a=0&b=0')
        assert response.status == 200
        json_response = await response.json()
        assert json_response['status'] == 'success'
        assert json_response['result'] == 0

if __name__ == '__main__':
    pytest.main()
