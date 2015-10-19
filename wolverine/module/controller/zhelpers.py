# encoding: utf-8
"""
Helper module for example applications. Mimics ZeroMQ Guide's zhelpers.h.
"""
from __future__ import print_function

import binascii
import logging
import msgpack
import os
from random import randint

import zmq

logger = logging.getLogger(__name__)


def dump(msg_or_socket):
    out = '\n-------data-packet-------'
    """Receives all message parts from socket, printing each frame neatly"""
    if isinstance(msg_or_socket, zmq.Socket):
        # it's a socket, call on current message
        msg = msg_or_socket.recv_multipart()
    else:
        msg = msg_or_socket
    for part in msg:
        out += "\n[%03d] " % len(part)
        try:
            out += part.decode('utf-8')
        except UnicodeDecodeError:
            try:
                out += str(msgpack.unpackb(part))
            except Exception:
                out += r"0x%s" % (binascii.hexlify(part).decode('ascii'))
    out += '\n' + '-'*25
    logger.debug(out)


def packb(data):
    try:
        return msgpack.packb(data, use_bin_type=True)
    except Exception:
        logger.error('error packing data', extra={'data': data}, exc_info=True)




def unpack(data):
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return unpackb(data)


def unpackb(data):
    try:
        return msgpack.unpackb(data, encoding='utf-8')
    except Exception:
        logger.warning('couldn\'t decode data' + str(data))
        return data


def set_id(zsocket):
    """Set simple random printable identity on socket"""
    identity = u"%04x-%04x" % (randint(0, 0x10000), randint(0, 0x10000))
    zsocket.setsockopt_string(zmq.IDENTITY, identity)


def zpipe(ctx):
    """build inproc pipe for talking to threads

    mimic pipe used in czmq zthread_fork.

    Returns a pair of PAIRs connected via inproc
    """
    a = ctx.socket(zmq.PAIR)
    b = ctx.socket(zmq.PAIR)
    a.linger = b.linger = 0
    a.hwm = b.hwm = 1
    iface = "inproc://%s" % binascii.hexlify(os.urandom(8))
    a.bind(iface)
    b.connect(iface)
    return a,b


ZMQ_EVENTS = {
    getattr(zmq, name): name.replace('EVENT_', '').lower().replace('_', ' ')
    for name in [i for i in dir(zmq) if i.startswith('EVENT_')]}


def event_description(event):
    """ Return a human readable description of the event """
    return ZMQ_EVENTS.get(event, 'unknown')
