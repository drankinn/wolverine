#!/usr/bin/env bash

docker run -d -p 1337:1337  -v `pwd`:/app --name micro-wolverine needleops/wolverine /env/bin/python -m wolverine.web -lDEBUG
