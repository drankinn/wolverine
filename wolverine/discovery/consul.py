import asyncio
import logging
import os
from consul import Check
from functools import wraps
from consul.aio import Consul
import types
from wolverine.discovery import MicroRegistry

logger = logging.getLogger(__name__)


class MicroConsul(MicroRegistry):
    def __init__(self):
        super(MicroConsul, self).__init__()
        self.name = 'registry'
        self.binds = {}
        self.health_tasks = {}
        self.run_tick = 3
        self.is_connected = False
        self._loop = None
        self._registry = None
        self.alive = False
        import wolverine.discovery
        self.default_settings = os.path.join(wolverine.discovery.__path__[0],
                                             'consul.ini')

    def register_app(self, app):
        self.app = app
        app.config.read(self.default_settings)
        self._loop = app.loop

    def run(self):
        self.config = self.app.config['DISCOVERY']
        self.host = self.config.get('HOST', 'localhost')
        self.port = int(self.config.get('PORT', '8500'))
        self.token = self.config.get('TOKEN', None)
        self.scheme = self.config.get('SCHEME', 'http')
        self.consistency = self.config.get('CONSISTENCY', 'default')
        self.dc = self.config.get('DC', None)
        self.verify = self.config.get('VERIFY', True)
        self._connect()
        logger.info('Consul - Initializing discovery listeners')

        def node_change(data):
            logger.info("node:" + str(data))
            pass

        self.bind_listener('node', 'node', node_change)
        self.run_task = self._loop.create_task(self.run_forever())

    @asyncio.coroutine
    def stop(self):
        self.alive = False

    def _connect(self):
        self._registry = Consul(self.host, self.port, self.token, self.scheme,
                                self.consistency, self.dc, self.verify,
                                loop=self._loop)
        self.agent = self._registry.agent
        self.catalog = self._registry.catalog
        self.health = self._registry.health
        self.kv = self._registry.kv

    def run_forever(self):
        self.alive = True
        while self.alive:
            if not self.is_connected:
                try:
                    agent_data = yield from self._registry.agent.self()
                    self.is_connected = agent_data['Member']['Status']
                    self.is_connected = True
                    self._bind_all()
                except Exception:
                    logger.error('failed to connect to agent')
                    self.is_connected = False
            yield from asyncio.sleep(self.run_tick)

    def _bind_all(self):
        if self.is_connected:
            for key, bind in self.binds.items():
                if bind.state in [0, -1]:
                    logger.info('binding ' + bind.bind_type + ' ' + bind.name)
                    self._loop.create_task(bind.run())

    def bind_listener(self, bind_type, name, func, **kwargs):
        bind = None
        single = kwargs.pop('singleton', False)
        if bind_type == 'kv':
            bind = ConsulKVBind(self, name, func, **kwargs)
        if bind_type == 'service':
            bind = ConsulServiceBind(self, name, func, **kwargs)
        if bind_type == 'health':
            bind = ConsulServiceHealthBind(self, name, func, **kwargs)
        if bind_type == 'node':
            bind = ConsulNodeBind(self, name, func, **kwargs)
        if isinstance(bind, ConsulBind):
            if bind.key in self.binds.keys():
                if not single:
                    bind = self.binds[bind.key]
                    bind.callbacks.append(func)
                    logger.warning("binding count for " + bind.key + ':',
                                   len(bind.callbacks))
                    if 'data' in kwargs:
                        bind.data.append(kwargs['data'])
                else:
                    logger.warning('discovery warning:not binding '
                                   'additional callbacks for singleton:' +
                                   name)
            else:
                self.binds[bind.key] = bind
        else:
            logger.warning("bind type not recognized: " + bind_type)
        return bind

    def listen(self, name, listen_type="kv", **kwargs):
        def listen_decorator(func):
            bind = self.bind_listener(listen_type, name, func, **kwargs)

            @wraps(func)
            def bind_run(data):
                for val in bind.run():
                    for callback in bind.callbacks:
                        return callback(val)

            return bind_run

        return listen_decorator

    def unwrap(self, data, data_type='kv'):
        if 'kv' == data_type:
            return unwrap_kv(data)
        if 'service' == data_type:
            return unwrap_service(data)
        if 'health' == data_type:
            return unwrap_health(data)

    @asyncio.coroutine
    def register(self, name, register_type='kv', value=None, **options):
        try:
            if 'kv' == register_type:
                yield from self.kv.put(name, value, **options)
            if 'service' == register_type:
                service_id = options.pop('service_id', name)
                check_ttl = options.pop('check_ttl', None)
                if check_ttl:
                    options['check'] = Check.ttl(check_ttl)
                ttl = None
                if 'ttl_ping' in options:
                    ttl = options.pop('ttl_ping')
                yield from self.agent.service.register(name, service_id=service_id,
                                                       **options)
                if ttl:
                    self.health_tasks[service_id] = self._loop.create_task(
                        self._health_ttl_ping(service_id, ttl))
            return True
        except Exception:
            logger.critical('failed to register with consul')
            return False

    @asyncio.coroutine
    def deregister(self, key, register_type='kv', **options):
        logger.info('deregistering ' + register_type + ' ' + key)
        if 'kv' == register_type:
            yield from self.kv.delete(key)
        if 'service' == register_type:
            yield from self.agent.service.deregister(key)
            if key in self.health_tasks:
                self.health_tasks[key].cancel()
                del self.health_tasks[key]
                logger.info('removed health task ' + key)

    @asyncio.coroutine
    def _health_ttl_ping(self, service_id, ttl):
        check_id = 'service:' + service_id
        alive = True
        while alive:
            try:
                data = \
                    yield from self.agent.check.ttl_pass(check_id)
                logger.info('health check returned with ' + str(data))
                yield from asyncio.sleep(ttl)
            except Exception:
                alive = False
        logger.info('health ttl ' + service_id + ' stopped')


class ConsulBind(object):
    bind_type = "vanilla"

    def __init__(self, client, name, callback, **kwargs):
        self.index = None
        self.name = name
        self.cache = {}
        self.registry = {}
        self.extra = []
        self.connect_retries = 10
        self.connect_delay = 3
        self.callbacks = []
        self.client = client
        self.key = self.bind_type + ':' + name
        self.state = 0
        if 'data' in kwargs:
            self.callbacks.append(
                self.wrap_callback(callback, kwargs.get('data')))
            del kwargs['data']
        else:
            self.callbacks.append(callback)
        self.params = kwargs

    @asyncio.coroutine
    def run(self):
        pass

    def wrap_callback(self, callback, app_data):
        def wrap(data):
            data = data + (app_data,)
            callback(data)

        return wrap

    def stop(self):
        self.state = 0

    def __del__(self):
        self.state = -1


class ConsulKVBind(ConsulBind):
    bind_type = "kv"

    def run(self):
        self.state = 1
        logger.debug('listening to key: ' + self.name)
        while self.state == 1:
            try:
                index, data = yield from self.client.kv.get(self.name,
                                                            **self.params)
                if self.cache != data:
                    self.cache = data
                    for callback in self.callbacks:
                        callback((index, data))
                self.index = index
            except asyncio.CancelledError:
                logger.warning('Value bind cancelled for ' + self.name)
                self.state = 0
                self.index = None
            except Exception:
                self.state = 0
                self.index = None


class ConsulServiceBind(ConsulBind):
    bind_type = 'service'

    def run(self):
        self.state = 1
        try:
            while self.state == 1:

                index, data = yield from self.client.catalog.service(
                    self.name,
                    index=self.index,
                    **self.params)
                if self.cache != data:
                    self.cache = data
                    for callback in self.callbacks:
                        callback((index, data))
                self.index = index
        except asyncio.CancelledError:
            logger.warning('service bind cancelled for ' + self.name)
        except Exception:
            logger.error('service bind failed', exc_info=True)
        finally:
            self.state = 0
            self.index = None


class ConsulServiceHealthBind(ConsulBind):
    bind_type = 'health'

    def run(self):
        self.state = 1
        try:
            while self.state == 1:
                response = yield from self.client.health.service(
                    self.name,
                    index=self.index,
                    **self.params)
                logger.debug('\n' + '-'*20 + '\nhealth data:\n' +
                             str(response) + '\n' + '-'*20)
                if response is not None:
                    index, data = response
                    if self.cache != data:
                        self.cache = data
                        for callback in self.callbacks:
                            response = callback((index, data))
                            if isinstance(response, types.GeneratorType):
                                yield from response
                    self.index = index
        except asyncio.CancelledError:
            logger.warning('health bind cancelled for ' + self.name)
        except Exception:
            logger.error('service health bind failed', exc_info=True)
        finally:
            self.state = 0
            self.index = None


class ConsulNodeBind(ConsulBind):
    bind_type = 'node'

    def load_default_agent_name(self):
        data = yield from self.client.agent.self()
        return data['Member']['Name']

    def run(self):
        self.state = 1
        try:
            while self.state == 1:
                if self.name == 'default':
                    self.name = yield from self.load_default_agent_name()
                index, data = yield from self.client.catalog.node(
                    self.name,
                    index=self.index,
                    **self.params)
                if self.cache != data:
                    self.cache = data
                    for callback in self.callbacks:
                        callback((index, data))
                self.index = index
        except asyncio.CancelledError:
            logger.warning('node bind cancelled for ' + self.name)
        except Exception:
            # logger.error('node bind failed', exc_info=True)
            logger.error('node bind failed')
        finally:
            self.client.is_connected = False
            self.state = 0
            self.index = None


def unwrap_kv(data):
    if data is not None and 'Value' in data:
        return data['Value'].decode('utf-8')
    else:
        return None


def unwrap_service(data):
    return data


def unwrap_health(data):
    ret = {'passing': {},
           'failing': {}}
    if data and len(data) > 0:
        services = list(data[1])
        for node in services:
            service = node['Service'].copy()
            checks = node['Checks']
            is_alive = True
            name = 'service:' + service['ID']
            for check in checks:
                if check['Status'] != 'passing':
                    is_alive = False
            if is_alive:
                ret['passing'][name] = service
            else:
                ret['failing'][name] = service
    return ret
