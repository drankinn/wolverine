import inspect
import logging
from wolverine.module import MicroModule
from wolverine.module.service import ServiceDef

logger = logging.getLogger(__name__)


class MicroController(MicroModule):
    def __init__(self):
        super(MicroController, self).__init__()
        self.handlers = []
        self.services = {}
        self.service_defs = {}
        self.clients = {}
        self.name = self.__class__.__name__

    def run(self):
        logger.info('running module ' + self.name)

        for name, service in self.services.items():
            self.app.loop.create_task(
                self.connect_service(name, service))
        for name, packet in self.service_defs.items():
            self.app.loop.create_task(
                self.app.registry.register(name, value=packet))

        for handler in self.handlers:
            self.register_handler(handler)
        self.app.router.sort_handlers()

    def register_handler(self, handler):
        name, handler_type, func, options = handler
        try:
            if 'server' == handler_type:
                route = name + '/' + options.pop('route', ".*")
                self.app.router.add_service_handler(route, func)
            if 'client' == handler_type:
                self.app.loop.create_task(
                    self.connect_client(name, func, **options))
            if 'data' == handler_type:
                self.app.loop.create_task(
                    self.connect_data(name, func, **options)
                )

        except Exception:
            logger.error('handler connect failed for ' + name, exc_info=True)

    def register_service(self, service):
        service_name = service.name or service.__class__.__name__
        service_def = ServiceDef(service_name, service.version)
        members = inspect.getmembers(service, predicate=inspect.ismethod)
        for name, func in members:
            if '__init__' == name:
                continue
            options = {'route': name}
            self.add_handler(service_name, 'server', func, **options)
            service_def.routes.append(service_name + '/' + name)
        self.service_defs[service_def.fqn()] = str(service_def)
        self.services[service_name] = service

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

    def data(self, name, **options):
        def decorator(f):
            self.add_handler(name, 'data', f, **options)
            return f
        return decorator

    def add_handler(self, name, handler_type, f, **options):
        self.handlers.append((name, handler_type, f, options))

    def connect_service(self, name, service):
        logger.debug('connecting handler service ' + name)

    def connect_client(self, name, func, **options):
        logger.debug('connecting handler client ' + name)

    def connect_data(self, name, func, **options):
        logger.debug('connecting handler data' + name)
