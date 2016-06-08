import asyncio
import logging
from optparse import OptionParser
import os
from wolverine import MicroApp
from wolverine.gateway import GatewayModule
from wolverine.web import WebModule

LOG_FORMAT = "%(asctime)s %(levelname)s" \
             " %(name)s:%(lineno)s %(message)s"


def web():

    log_level = logging.INFO
    usage = "usage: %prog [options] arg"
    parser = OptionParser(usage)
    parser.add_option("-l", "--log-level", dest="log_level",
                      help="log level one of "
                           "(DEBUG, INFO, WARNING, ERROR, Critical)",
                      default="ERROR")
    (options, args) = parser.parse_args()
    if options.log_level:
        log_level = getattr(logging, options.log_level.upper())
    logging.basicConfig(level=log_level,
                        format=LOG_FORMAT)

    loop = asyncio.get_event_loop()
    app = MicroApp(loop=loop)
    gateway = GatewayModule()
    app.register_module(gateway)
    web_console = WebModule()
    app.register_module(web_console)
    app.run()

    def shutdown(sig_name):
        if sig_name in MicroApp.SIG_NAMES:
            app.web.stop_server()
            tasks = asyncio.Task.all_tasks(loop)
            for task in tasks:
                try:
                    task.cancel()
                except Exception:
                    pass
            loop.stop()
    app.add_shutdown_handler(shutdown)
    app.web.create_server()
    loop.run_forever()

if __name__ == '__main__':
    web()
