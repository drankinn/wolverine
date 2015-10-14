import asyncio
from wolverine.routers import MicroRouter


class MicroModule(object):
    def __init__(self):
        self.handlers = []
        self.name = self.__class__.__name__
        self.router = MicroRouter()

    def run(self):
        print('running module', self.name)

    @asyncio.coroutine
    def exit(self):
        print('closing module', self.name)

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

    def register_app(self, app, **options):
        """Called by Micro App to register a module and it's routes.
        binds callback for consul and initializes zmq endpoints

        :param app:
        :param options:
        :return:
        """
        self.app = app
        for handler in self.handlers:
            self._connect_handler(handler)

    def _connect_handler(self, handler):
        name, handler_type, func, options = handler
        if 'server' == handler_type:
            self.app.loop.create_task(
                self._connect_service(name, func, **options))
        if 'client' == handler_type:
            self.app.loop.create_task(
                self._connect_client(name, func, **options))

    def add_handler(self, name, handler_type, f, **options):
        self.handlers.append((name, handler_type, f, options))

    def add_client(self, name, func, **options):
        print('adding client', name)

    def _connect_service(self, name, func, **options):
        print('connecting handler service', name)

    def _connect_client(self, name, func, **options):
        print('connecting handler client', name)
