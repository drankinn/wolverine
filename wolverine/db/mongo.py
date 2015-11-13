import logging
from asyncio_mongo import Pool
import os
from wolverine.db import MicroDB

logger = logging.getLogger(__name__)


class MicroMongoDB(MicroDB):
    def __init__(self):
        super(MicroMongoDB, self).__init__()
        self.name = 'mongo'
        self.pool = None
        import wolverine.db
        self.default_settings = os.path.join(wolverine.db.__path__[0],
                                             'mongo.ini')

    def register_app(self, app):
        self.app = app
        app.config.read(self.default_settings)

    def read_config(self):
        self.config = self.app.config[self.name.upper()]

    def run(self):
        logger.debug('running MongoDB module')
        self.read_config()
        self.host = os.getenv("MONGO_HOST",
                              self.config.get('HOST', 'localhost'))
        self.port = os.getenv("MONGO_PORT", self.config.get('PORT', '27017'))
        self.default_db = os.getenv("MONGO_DB",
                                    self.config.get('DB', '_global'))
        self.pool_size = os.getenv("MONGO_POOL_SIZE",
                                   self.config.get('POOL_SIZE', 10))
        self.pool = yield from Pool.create(host=self.host,
                                           port=self.port,
                                           poolsize=int(self.pool_size),
                                           db=self.default_db)

    def __getattr__(self, name):
        try:
            return getattr(self.pool, name)
        except:
            logger.error('error connecting to mongo db ' + name, exc_info=True)
            return None
