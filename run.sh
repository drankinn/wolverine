#!/usr/bin/env bash

docker run -d -p 1337:1337 -e "DISCOVERY_HOST=172.17.0.3"  -v `pwd`:/app --name micro-wolverine needleops/wolverine /env/bin/python -m wolverine.web -lDEBUG
