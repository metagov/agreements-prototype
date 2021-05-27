import sched
import time
import logging
import traceback
from pathlib import Path
import sys

sys.path.append(Path(__file__).parent.absolute())

from app.database import update

logger = logging.getLogger('app.scheduler')

s = sched.scheduler(time.time, time.sleep)

def scheduled_update(sc):
    s.enter(60, 1, scheduled_update, (sc,))
    before = time.time()
    
    try:
        num_processed, last_status = update.run()

        # only sends update if new statuses were processed so the console doesn't get spammed
        if num_processed > 0:
            logger.info('Processed {} new statuses since #{} in {:.3f} seconds'.format(num_processed, last_status, time.time() - before))

    except Exception as e:
        logger.warn(traceback.format_exc())

s.enter(0, 1, scheduled_update, (s,))
s.run()