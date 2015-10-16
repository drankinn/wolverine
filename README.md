Wolverine
==========
A Micro-Service framework built on python 3.5 and asyncio

requirements for using as a package:
python <= version 3.5



EXAMPLES
=========

There is an example Ping Pong demo that you can use to try it.

assumptions:
- you have a consul service listening on localhost port 8500
- you have python 3.5 or greater as your interpreter
- you've ran pip install -r requirements.txt

to run the pong service:
python -m examples.ping_pong pong -d0 -a -lINFO


to run the ping client:

python -m examples.ping_pong ping -d1 -p 1992 -a -t 5 -lINFO 


for some real fun:

time python -m examples.ping_pong ping -d0 -p 1337 -a -t 5000 -lINFO
