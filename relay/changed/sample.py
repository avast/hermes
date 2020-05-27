
from salmon.routing import route, route_like, stateless, nolocking
from salmon import handlers, queue
import os
import logging

if "SALMON_SETTINGS_MODULE" in os.environ:
    from tests.testing_settings import relay
else:
    from config.settings import relay


@route("(address)@(host)", address=".+")
def START(message, address=None, host=None):
    logging.debug("MESSAGE to %s@%s", address, host)


@route_like(START)
@stateless
def FORWARD(message, address=None, host=None):
    relay.deliver(message)
