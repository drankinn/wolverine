
import logging
from optparse import OptionParser
from examples.mongo import mongo

LOG_FORMAT = "%(asctime)s %(levelname)s" \
             " %(name)s:%(lineno)s %(message)s"


def main():

    log_level = logging.INFO

    usage = "usage: %prog [options] arg"
    parser = OptionParser(usage)
    parser.add_option("-H", "--host", dest="host",
                      help="host to bind to", default='localhost')
    parser.add_option("-p", "--port", dest="port",
                      help="port to bind to", default='9210')
    parser.add_option("-v", "--version", dest="version",
                      help="app version", default='1')
    parser.add_option("-l", "--log-level", dest="loglevel",
                      help="log level one of "
                           "(DEBUG, INFO, WARNING, ERROR, Critical)",
                      default="ERROR")

    (options, args) = parser.parse_args()
    if options.loglevel:
        log_level = getattr(logging, options.loglevel.upper())
    logging.basicConfig(level=log_level,
                        format=LOG_FORMAT)

    mongo(options)


if __name__ == "__main__":
    main()

