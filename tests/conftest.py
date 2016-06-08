import pytest

from wolverine import MicroApp
from wolverine.db.redis import MicroRedisDB


@pytest.fixture
def redis_app():
    test_app = MicroApp()
    redis = MicroRedisDB()
    test_app.register_module(redis)
    return test_app
