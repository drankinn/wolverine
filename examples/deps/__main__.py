import logging
from optparse import OptionParser
from examples.deps import run

LOG_FORMAT = "%(message)s"


def main():

    log_level = logging.INFO

    usage = "usage: %prog [options] arg"
    parser = OptionParser(usage)
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

    run()


if __name__ == "__main__":
    main()

