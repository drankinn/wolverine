import socket
import logging
from uuid import uuid1

import functools
import os
from wolverine.module.controller.zmq import ZMQMicroController

logger = logging.getLogger(__name__)


class GatewayModule(ZMQMicroController):
    def __init__(self):
        super(GatewayModule, self).__init__()
        self.name = 'gateway'
        self.gateway_id = str(uuid1())[:8]
        self.default_settings = os.path.join(__path__[0],
                                             'settings.ini')
        self.client_services = {}
        self.used_ports = []
        self.recycled_ports = []

    def register_app(self, app):
        self.app = app
        app.config.read(self.default_settings)

    def read_config(self):
        config = self.app.config['GATEWAY']
        default_host = 'tcp://' + socket.gethostbyname(socket.gethostname())
        self.gw_host = config.get('GATEWAY_HOST', default_host)
        self.gw_start_port, self.gw_end_port = config.get(
            'GATEWAY_PORT_RANGE').split('-')
        self.gw_start_port = int(self.gw_start_port)
        self.gw_end_port = int(self.gw_end_port)

    def run(self):
        logger.info('running the gateway')
        self.read_config()
        self.bind_service_data()
        super(GatewayModule, self).run()

    def get_gw_port(self):
        port = self.gw_start_port
        if len(self.recycled_ports) > 0:
            port = self.recycled_ports.pop(0)
        elif len(self.used_ports) > 0:
            port = max(self.used_ports) + 1
        if port > self.gw_end_port:
            logger.warning(
                'using port {}, which is above '
                'the configured range of {}-{} '
                .format(port, self.gw_start_port, self.gw_end_port))
        self.used_ports.append(int(port))
        return port

    def bind_service_data(self):
        @self.data('service:', recurse=True)
        def service_data(data):
            service_names = []
            for d in data:
                service_id = self.gateway_id + '_' + str(d['version'])
                service_name = d['name'] + ':' + service_id
                service_names.append(service_name)
                if service_name not in self.app.router.clients.keys():
                    self.create_client(d)
            removed = list(set(self.app.router.clients.keys()) -
                           set(service_names))
            for service_name in removed:
                self.remove_client(service_name)

    def remove_client(self, name):
        logger.debug('removing client for service ' + name)
        data = self.client_services[list(name.split(':'))[0]][name]
        port = int(data['port'])
        if port in self.used_ports:
            self.used_ports.remove(port)
        self.recycled_ports.append(port)
        del self.client_services[list(name.split(':'))[0]][name]
        self.app.loop.create_task(
            self.app.router.remove_client(name))

    def create_client(self, data):
        service_id = self.gateway_id + '_' + str(data['version'])
        service_name = data['name'] + ':' + service_id
        port = self.get_gw_port()
        data['port'] = port
        if data['name'] not in self.client_services:
            self.client_services[data['name']] = {}
        self.client_services[data['name']][service_name] = data
        options = {
            'service_id': service_id,
            'address': self.gw_host,
            'port': port,
            'tags': ['version:' + str(data['version'])],
            'async': True
        }
        route = data['routes'][0]
        self.app.loop.create_task(
            self.connect_client(data['name'],
                                functools.partial(
                                    self.callback, route, service_name,
                                    str(data['version'])),
                                **options))
        logger.debug('data: ' + str(data))

    def callback(self, route, service_name, version):
        pass
