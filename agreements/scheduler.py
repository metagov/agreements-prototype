from app.database import update
import sched, time, datetime
import logging, traceback

logger = logging.getLogger('app.scheduler')

s = sched.scheduler(time.time, time.sleep)

def scheduled_update(sc):
    s.enter(60, 1, scheduled_update, (sc,))
    before = time.time()
    
    try:
        num_processed, last_status = update.run()
    except Exception as e:
        logger.warn(traceback.format_exc())

    logger.info('Processed {} new statuses since #{} in {:.3f} seconds'.format(num_processed, last_status, time.time() - before))

s.enter(0, 1, scheduled_update, (s,))
s.run()