#!/usr/bin/env bash

source $HOME/hermes/salmon-relay/bin/activate
cd $HOME/hermes/salmon-relay/myproject
python3 salmondeleteold.py
deactivate
