"""
Implements a handler that puts every message it receives into
the run/queue directory.  It is intended as a debug tool so you
can inspect messages the server is receiving using mutt or
the salmon queue command.
"""

import logging

from salmon import handlers, queue
from salmon.routing import route_like, stateless, nolocking
import re

def queue_handler():
    @route("(to)@(host)", to=".+", host=".+")
    @stateless
    @nolocking
    def START(message, to=None, host=None):
        logging.debug("MESSAGE to %s@%s added to queue.", to, host)
        q = queue.Queue('run/queue')
        email = "%s@%s" % (to, host)
        message = str(message).replace("%", "%%")
        new_msg = re.sub(r'(?m)^\To:.*\n?', 'To: %s\n', message, 1) % (email,)
        q.push(new_msg)
