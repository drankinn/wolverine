import logging
from wolverine.module import MicroModule
from wolverine.routers import MicroRouter

logger = logging.getLogger(__name__)


class MicroService(MicroModule):
    def __init__(self):
        super(MicroService, self).__init__()
        self.handlers = []
        self.name = self.__class__.__name__
        self.router = MicroRouter()

    def run(self):
        logger.info('running module ' + self.name)
        for handler in self.handlers:
            self.connect_handler(handler)

    def handler(self, service, **options):
        """Collects data to build zmq endpoints based on consul services
        actual binding and initialization is deferred to module registration

        :param rule:
        :param options:
        :return:
        """

        def decorator(f):
            handler_type = options.pop("handler_type", "server")
            self.add_handler(service, handler_type, f, **options)
            return f

        return decorator

    def client(self, name, **options):
        def decorator(f):
            self.add_handler(name, 'client', f, **options)
            return f
        return decorator

    def connect_handler(self, handler):
        name, handler_type, func, options = handler
        try:
            if 'server' == handler_type:
                self.app.loop.create_task(
                    self.connect_service(name, func, **options))
            if 'client' == handler_type:
                self.app.loop.create_task(
                    self.connect_client(name, func, **options))
        except Exception:
            logger.error('handler connect failed for ' + name, exc_info=True)

    def add_handler(self, name, handler_type, f, **options):
        self.handlers.append((name, handler_type, f, options))

    def connect_service(self, name, func, **options):
        logger.debug('connecting handler service ' + name)

    def connect_client(self, name, func, **options):
        logger.debug('connecting handler client ' + name)