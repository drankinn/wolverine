import asyncio
import logging
from wolverine.module.service import ServiceMessage, MicroService

logger = logging.getLogger(__name__)


class PingPongService(MicroService):

    def __init__(self, **options):
        self.delay = options.pop('delay', 1)
        self.routing = options.pop('routing', False)
        version = options.pop('version', '1')
        super(PingPongService, self).__init__('ping', version=version)
        self.name = 'ping'
        self.options = {}

    def ping1(self, data):
        logger.debug('--ping1 handler--')
        logger.debug('data: ' + str(data))
        yield from asyncio.sleep(self.delay)
        return data

    def ping(self, data):
        logger.debug('data: ' + str(data))
        yield from asyncio.sleep(self.delay)
        response = ServiceMessage()
        response.data = data
        return response

    def ping2(self, data):
        logger.debug('--ping1 handler--')
        logger.debug('data: ' + str(data))
        yield from asyncio.sleep(self.delay)
        return data

