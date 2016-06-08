import asyncio
import os
import logging

try:
    from asyncio_redis import Pool
except Exception as ex:
    pass

from wolverine.db import MicroDB

logger = logging.getLogger(__name__)


class MicroRedisDB(MicroDB):
    def __init__(self):
        super().__init__()
        self.name = 'redis'
        self.pool = None
        self.create_pool_task = None
        import wolverine.db
        self.default_settings = os.path.join(wolverine.db.__path__[0],
                                             'redis.ini')

    def configure(self, app):
        super().configure(app)
        app.config.read(self.default_settings)

    def read_config(self):
        self.config = self.app.config[self.name.upper()]

    def init(self):
        self.read_config()
        self.host = os.getenv("REDIS_HOST",
                              self.config.get('HOST', 'localhost'))
        self.port = os.getenv("REDIS_PORT", self.config.get('PORT', '6379'))
        self.default_db = os.getenv("REDIS_DB",
                                    self.config.get('DB', '0'))
        self.pool_size = os.getenv("REDIS_POOL_SIZE",
                                   self.config.get('POOL_SIZE', 10))
        self.ready.set()
        return


    async def stop(self):
        tasks = [c.protocol._reader_f for c in self.pool._connections ]
        self.pool.close()
        await asyncio.wait(tasks)

    @self.requires_init()
    async def db(self):
        if not self.ready.is_set():
            self.init()
        await self.ready.wait()  # block until the module has loaded
        if self.pool is None:
            if self.create_pool_task is not None:
                while self.create_pool_task is not None or self.pool is None:
                    await asyncio.sleep(1)
                return self.pool
            self.create_pool_task = asyncio.get_event_loop().create_task(Pool.create(host=self.host,
                                          port=int(self.port),
                                          poolsize=int(self.pool_size),
                                          db=int(self.default_db)))
            await asyncio.wait_for(self.create_pool_task, 10)
            try:
                self.pool = self.create_pool_task.result()
            except Exception as ex:
                print(ex)
            self.create_pool_task = None
        return self.pool

    async def sub(self):
        db = await self.db()
        subscriber = await db.start_subscribe()
        return subscriber
