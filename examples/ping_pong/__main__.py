import logging
from optparse import OptionParser
from examples.ping_pong import ping_pong

LOG_FORMAT = "%(asctime)s %(levelname)s" \
             " %(name)s:%(lineno)s %(message)s"


def main():

    log_level = logging.INFO

    usage = "usage: %prog [options] arg"
    parser = OptionParser(usage)
    parser.add_option("-p", "--port", dest="port",
                      help="port to bind to", default='9210')
    parser.add_option("-v", "--version", dest="version",
                      help="app version", default='1')
    parser.add_option("-d", "--delay", dest="delay",
                      help="simulated workload delay", default="1")
    parser.add_option("-t", "--times", dest="times",
                      help="number of times to ping", default="-1")
    parser.add_option("-r", "--routing", dest="routing", action='store_true',
                      help="enable advanced routing")
    parser.add_option("-a", "--async", dest="async", action='store_true',
                      help="enable async client/service worker")
    parser.add_option("-l", "--log-level", dest="loglevel",
                      help="log level one of "
                           "(DEBUG, INFO, WARNING, ERROR, Critical)",
                      default="ERROR")

    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error("incorrect number of arguments")
    if options.loglevel:
        log_level = getattr(logging, options.loglevel.upper())
    logging.basicConfig(level=log_level,
                        format=LOG_FORMAT)

    ping_pong(args[0], options)



if __name__ == "__main__":
    main()
