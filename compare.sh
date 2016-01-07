#!/usr/bin/with-contenv sh

DOCKERFILE_DIFF=`diff -q /app/Dockerfile /data/Dockerfile`
if [ "$DOCKERFILE_DIFF" == "" ]
    then
        REQUIREMENTS_DIFF=`diff -q /app/requirements.txt /data/requirements.txt`
        if [ "$REQUIREMENTS_DIFF" != "" ]
            then
                exit 1
        fi
    else
        exit 1
fi