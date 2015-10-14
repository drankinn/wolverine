from optparse import OptionParser
from examples.ping_pong import ping_pong


def main():
    usage = "usage: %prog [options] arg"
    parser = OptionParser(usage)
    parser.add_option("-p", "--port", dest="port",
                      help="port to bind to", default='9210')
    parser.add_option("-c", "--concurrent", dest="concurrent",
                      help="concurrent workers", default="1")
    parser.add_option("-d", "--delay", dest="delay",
                      help="simulated workload delay", default="1")
    parser.add_option("-t", "--times", dest="times",
                      help="number of times to ping", default="-1")
    parser.add_option("-r", "--routing", dest="routing", action='store_true',
                      help="enable advanced routing")
    parser.add_option("-a", "--async", dest="async", action='store_true',
                      help="enable async client")
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error("incorrect number of arguments")
    if 'ping' in args:
        ping_pong('client', options)
    if 'pong' in args:
        ping_pong('server', options)


if __name__ == "__main__":
    main()
