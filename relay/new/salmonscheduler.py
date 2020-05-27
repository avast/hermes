"""salmonscheduler module.

This module takes care of the number of relayed emails 
per time unit specified in salmon.yaml
Author: Silvie Chlupová
Date    Created: 09/17/2019
"""

import datetime
import logging
from apscheduler.scheduler import Scheduler
from salmon import server
from salmon import utils


def resetcounter():
    """Function resets the counter of relayed emails during the last x minutes."""
    server.QueueReceiver.totalRelay = 0
    logging.info("[+] (salmonscheduler.py) - Resetting counters!")


def schedule():
    """Schedule a timer before the counter of relayed emails is reset."""
    sched = Scheduler()
    duration = utils.settings.data["relay"]["schedulertime"]
    sched.add_interval_job(resetcounter, minutes=duration)
    sched.start()
    logging.info(
        "[+] (salmonscheduler.py) - Salmon scheduler started at %s and will execute every %d minutes "
        % (datetime.datetime.now(), duration)
    )
