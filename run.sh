#!/usr/bin/env bash

docker run -d --dns 172.17.42.1 --dns 8.8.8.8 -p 8080:8080  -v `pwd`:/app --name micro-wolverine needleops/wolverine /env/bin/python -m wolverine.web -lDEBUG
