#!/bin/bash

cd $HOME

salmon_directory=`find -name hermes -print -quit`
cd $salmon_directory/salmon-relay/
. bin/activate
cd myproject/

if [ "$#" -eq 1 ]; then
    if [ "$1" == "start" ]; then
        salmon-relay start
    elif [ "$1" == "status" ]; then
        salmon-relay status
    elif [ "$1" == "stop" ]; then
        salmon-relay stop
    elif [ "$1" == "restart" ]; then
        salmon-relay stop
        salmon-relay start
    else
        echo "unknown command"
        deactivate
        exit 1
    fi
else
    if [ "$#" -eq 2 -a "$1" == "start" -a "$2" == "--force" ]; then
        salmon-relay stop
        salmon-relay start
    else
        echo "unknown command"
        deactivate
        exit 1
    fi
fi

deactivate
exit 0
