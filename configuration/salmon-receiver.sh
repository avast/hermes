#!/bin/bash

cd $HOME

salmon_directory=`find -name hermes -print -quit`
cd $salmon_directory/salmon-receiver/
. bin/activate
cd myproject/

if [ "$#" -eq 1 ]; then
    if [ "$1" == "start" ]; then
        salmon-receiver start
    elif [ "$1" == "status" ]; then
        salmon-receiver status
    elif [ "$1" == "stop" ]; then
        salmon-receiver stop
    elif [ "$1" == "restart" ]; then
        salmon-receiver stop
        salmon-receiver start
    else
        echo "unknown command"
        deactivate
        exit 1
    fi
else
    if [ "$#" -eq 2 -a "$1" == "start" -a "$2" == "--force" ]; then
        salmon-receiver stop
        salmon-receiver start
    else
        echo "unknown command"
        deactivate
        exit 1
    fi
fi

deactivate
exit 0
