import asyncio
import signal
import functools
import sys
from wolverine.discovery import MicroRegistry


class MicroApp(object):
    SIG_NAMES = ('SIGINT', 'SIGTERM', 'SIGHUP')

    _default_registry = MicroRegistry

    def __init__(self, loop=None, registry=None):
        self.tasks = []
        self.modules = []
        self.router = {}
        if registry is not None and not isinstance(registry, MicroRegistry):
            print('registry must be an instance of MicroRegistry')
            return
        self.registry = registry
        if loop is None:
            self.loop = asyncio.get_event_loop()
        else:
            self.loop = loop

        def _exit(sig_name):
            self.loop.create_task(self.exit(sig_name))

        for sig in self.SIG_NAMES:
            self.loop.add_signal_handler(getattr(signal, sig),
                                         functools.partial(_exit,
                                                           sig))

    def register_module(self, module):
        print("registering module", module.name)
        module.register_app(self)
        self.modules.append(module)

    def run(self):
        if self.registry is None:
            self.registry = self._default_registry()
        self.registry.run()
        for module in self.modules:
            module.run()
        self.loop.run_forever()
        print('closing loop')
        try:
            self.loop.close()
        except Exception as ex:
            print('boom', ex)

    def exit(self, sig_name):
        if sig_name in self.SIG_NAMES:
            for module in self.modules:
                yield from module.exit()
            tasks = asyncio.Task.all_tasks(self.loop)
            for task in tasks:
                try:
                    task.cancel()
                except Exception as e:
                    print(e)
            self.loop.stop()

