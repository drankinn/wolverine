Wolverine
==========
A Micro-Service framework built on python 3.5 and asyncio

requirements for using as a package:
python >= version 3.5

CONFIGURATION
-------------
when a MicroApp instance is ran, it looks for a settings.ini file in the 
current directory.  This location can be overridden by passing in a config_file
option to the class constructor which is the string path to the config file.

These config options will be overlayed on the defaults.

The full app configuration can be accessed with a call to app.config
A configparser.ConfigParser instance will be returned.
 
Config files have the format:
 
[APP]
NAME = WOLVERINE
ROUTER = wolverine.routers.MicroRouter
REGISTRY = wolverine.discovery.MicroRegistry

[DB]
HOST = localhost
PORT = 3306


EXAMPLES
---------

There is an example Ping Pong demo that you can use to try it.

assumptions:
- you have a consul service listening on localhost port 8500
- you have python 3.5 or greater as your interpreter
- you've ran pip install -r requirements.txt

also I recommend installing the zmq and zmq dev libraries for better performance

on ubuntu that is apt-get install libzmq3-dev

to run the pong service:
python -m examples.ping_pong pong -d0 -a -lINFO


to run the ping client:

python -m examples.ping_pong ping -d1 -p 1992 -a -t 5 -lINFO 


for some real fun:

time python -m examples.ping_pong ping -d0 -p 1337 -a -t 5000 -lINFO
