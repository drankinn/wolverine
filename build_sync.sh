#!/usr/bin/env bash
curr_dir=`pwd`
BUILD_REQUIRED=`docker run --rm -v $curr_dir:/data needleops/wolverine /data/compare.sh | grep 'compare.sh exit' | awk '{print $3}'`
if (( $BUILD_REQUIRED != 0 ))
  then
    #check if requirements file has changed
    echo "Docker build required"
    #./build.sh
  else
    echo "build up to date"
fi