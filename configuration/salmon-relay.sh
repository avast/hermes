#!/bin/bash

cd $HOME

salmon_directory=`find -name salmon-honeypot -print -quit`
cd $salmon_directory/salmon-relay/
. bin/activate
cd myproject/

if [ "$#" -eq 1 ]; then
    if [ "$1" == "start" ]; then
        salmon start
    elif [ "$1" == "status" ]; then
        salmon status
    elif [ "$1" == "stop" ]; then
        salmon stop
    elif [ "$1" == "restart" ]; then
        salmon stop
        salmon start
    else
        echo "unknown command"
        deactivate
        exit 1
    fi
else
    if [ "$#" -eq 2 -a "$1" == "start" -a "$2" == "--force" ]; then
        salmon stop
        salmon start
    else
        echo "unknown command"
        deactivate
        exit 1
    fi
fi

deactivate
exit 0
