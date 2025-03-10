import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

class TestSumHandler(AioHTTPTestCase):

    async def get_application(self):
        return await init_app()

    @unittest_run_loop
    async def test_sum_valid_numbers(self):
        response = await self.client.get('/sum?a=3&b=5')
        assert response.status == 200
        json_response = await response.json()
        assert json_response['result'] == 8
        assert json_response['status'] == 'success'

    @unittest_run_loop
    async def test_sum_missing_parameters(self):
        response = await self.client.get('/sum?a=3')
        assert response.status == 400
        json_response = await response.json()
        assert json_response['error'] == 'Параметры a и b обязательны.'

    @unittest_run_loop
    async def test_sum_non_numeric_parameters(self):
        response = await self.client.get('/sum?a=three&b=five')
        assert response.status == 400
        json_response = await response.json()
        assert json_response['error'] == 'Параметры a и b должны быть числами.'

    @unittest_run_loop
    async def test_sum_empty_parameters(self):
        response = await self.client.get('/sum?a=&b=')
        assert response.status == 400
        json_response = await response.json()
        assert json_response['error'] == 'Параметры a и b обязательны.'

    @unittest_run_loop
    async def test_sum_large_numbers(self):
        response = await self.client.get('/sum?a=1e+100&b=1e+100')
        assert response.status == 200
        json_response = await response.json()
        assert json_response['result'] == 2e+100
        assert json_response['status'] == 'success'

    @unittest_run_loop
    async def test_sum_negative_numbers(self):
        response = await self.client.get('/sum?a=-3&b=-5')
        assert response.status == 200
        json_response = await response.json()
        assert json_response['result'] == -8
        assert json_response['status'] == 'success'

if __name__ == '__main__':
    pytest.main()