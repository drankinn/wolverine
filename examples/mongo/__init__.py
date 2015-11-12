import asyncio
import os
from examples.mongo.service import MongoService
from wolverine.db.mongo import MicroMongoDB
from wolverine.module.controller.zmq import ZMQMicroController


def mongo(options):
    from wolverine import MicroApp
    loop = asyncio.get_event_loop()
    config_file = os.path.join(__path__[0], 'settings.ini')
    app = MicroApp(loop=loop, config_file=config_file)
    mongo_db = MicroMongoDB()
    app.register_module(mongo_db)
    controller = ZMQMicroController()
    app.register_module(controller)
    service_def = MongoService(app)
    controller.register_service(service_def)
    app.run()
