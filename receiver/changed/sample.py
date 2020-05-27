from salmon.routing import route, route_like, stateless, nolocking
from salmon import handlers, queue
import logging
import re

@route("(to)@(host)", to=".+", host=".+")
@stateless
def LOG(message, to=None, host=None):
    """This is stateless and handles every email no matter what, logging what it receives."""
    logging.debug("MESSAGE to %s@%s" % (to, host))

@route_like(LOG)
@stateless
@nolocking
def START(message, to=None, host=None):
    """
    @stateless and routes however handlers.log.START routes (everything).
    Has @nolocking, but that's alright since it's just writing to a maildir.
    """
    logging.debug("MESSAGE to %s@%s added to queue.", to, host)
    q = queue.Queue('run/queue')
    q.push(message)
