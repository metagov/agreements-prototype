import logging
import tweepy

from .. import core
from .parser import Parser
from .metadata import Metadata

logger = logging.getLogger(__name__)

def run():
    # core.db.drop_tables() # clears database

    meta = Metadata(core.db)
    parser = Parser(core.db, core.api)

    last_status_parsed = meta.retrieve('last_status_parsed')

    new_statuses = []

    # logger.info(f'Update started at status #{last_status_parsed}')

    # collects new statuses in reverse chronological order
    for status in tweepy.Cursor(
        core.api.mentions_timeline, 
        tweet_mode="extended", # needed to get full text for longer tweets
        since_id=last_status_parsed, # won't iterate through tweets already in database
        count=200
    ).items():
        new_statuses.append(status)


    # iterates through statuses in chronological order
    for status in reversed(new_statuses):
        try:
            logger.info('')
            logger.info(f'NEW STATUS: [{status.id_str}] -> {status.full_text}')
            parser.parse(status)
        except tweepy.error.TweepError as error:
            if error.api_code == 385:
                logger.warn('Cannot reply to tweet')
            elif error.api_code == 187:
                logger.warn('Duplicate tweet')
            else:
                logger.warn(f'Unknown tweepy error: {error.api_code}')

        # updates last status id -> next mentions timeline won't see already parsed tweets
        if status.id > last_status_parsed:
            meta.update('last_status_parsed', status.id)
    
    return (len(new_statuses), last_status_parsed)
