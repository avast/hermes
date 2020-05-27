#!/usr/bin/env bash

source $HOME/salmon-honeypot/salmon-relay/bin/activate
cd $HOME/salmon-honeypot/salmon-relay/myproject
python3 salmondeleteold.py
deactivate
