import asyncio
import pytest


@pytest.mark.asyncio
async def test_redis_pool(redis_app):
    await redis_app.run()
    db = await redis_app.redis.db()
    assert db is not None
    assert db.connections_connected == db._poolsize
    db2 = await redis_app.redis.db()
    assert db == db2
    await asyncio.get_event_loop().create_task(redis_app.app_stop('SIGTERM'))


@pytest.mark.asyncio
async def test_redis_get_set(redis_app):
    redis_app.run()
    db = await redis_app.redis.db()
    is_set = await db.set('test', 'value')
    assert is_set
    val = await db.get('test')
    assert val == 'value'
    await asyncio.get_event_loop().create_task(redis_app.app_stop('SIGTERM'))


@pytest.mark.asyncio
async def test_redis_pubsub(redis_app):
    await redis_app.run()
    db = await redis_app.redis.db()
    subscriber = await redis_app.redis.sub()

    async def _listen():
        await subscriber.subscribe(['test'])
        reply = await subscriber.next_published()
        return reply.value

    task = asyncio.get_event_loop().create_task(_listen())

    async def _publish():
        await db.publish('test', 'test-val')

    asyncio.get_event_loop().create_task(_publish())
    val = await task
    assert val == 'test-val'
    await asyncio.get_event_loop().create_task(redis_app.app_stop('SIGTERM'))


@pytest.mark.asyncio
async def test_redis_set_on_exists(redis_app):
    await redis_app.run()
    db = await redis_app.redis.db()
    try:
        ret1 = await db.set("test_on_exists", 'test1', expire=10,
                            only_if_not_exists=True)
        assert ret1.status == 'OK'
        ret2 = await db.set("test_on_exists", 'test2', expire=10,
                            only_if_not_exists=True)
        assert ret2 is None
    finally:
        await db.delete(['test_on_exists'])

    await asyncio.get_event_loop().create_task(redis_app.app_stop('SIGTERM'))