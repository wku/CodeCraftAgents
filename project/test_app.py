import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
import json

class TestSumHandler(AioHTTPTestCase):

    async def get_application(self):
        return await init_app()

    @unittest_run_loop
    async def test_sum_valid(self):
        response = await self.client.get('/sum?a=3&b=5')
        assert response.status == 200
        data = await response.json()
        assert data['result'] == 8

    @unittest_run_loop
    async def test_sum_with_floats(self):
        response = await self.client.get('/sum?a=3.5&b=2.5')
        assert response.status == 200
        data = await response.json()
        assert data['result'] == 6.0

    @unittest_run_loop
    async def test_sum_missing_a(self):
        response = await self.client.get('/sum?b=5')
        assert response.status == 400
        data = await response.json()
        assert data['error'] == "Параметры 'a' и 'b' обязательны."

    @unittest_run_loop
    async def test_sum_missing_b(self):
        response = await self.client.get('/sum?a=3')
        assert response.status == 400
        data = await response.json()
        assert data['error'] == "Параметры 'a' и 'b' обязательны."

    @unittest_run_loop
    async def test_sum_invalid_a(self):
        response = await self.client.get('/sum?a=abc&b=5')
        assert response.status == 400
        data = await response.json()
        assert 'could not convert string to float' in data['error']

    @unittest_run_loop
    async def test_sum_invalid_b(self):
        response = await self.client.get('/sum?a=3&b=xyz')
        assert response.status == 400
        data = await response.json()
        assert 'could not convert string to float' in data['error']

    @unittest_run_loop
    async def test_sum_no_params(self):
        response = await self.client.get('/sum')
        assert response.status == 400
        data = await response.json()
        assert data['error'] == "Параметры 'a' и 'b' обязательны."

    @unittest_run_loop
    async def test_sum_large_numbers(self):
        response = await self.client.get('/sum?a=1e+100&b=1e+100')
        assert response.status == 200
        data = await response.json()
        assert data['result'] == 2e+100

if __name__ == '__main__':
    pytest.main()