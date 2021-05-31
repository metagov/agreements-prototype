import json, logging
import tweepy
from tinydb import TinyDB
from .auth import auth
from .database.metadata import Metadata

# setting up app level logger to log in stdout and to a file
root_logger = logging.getLogger('app')
root_logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter(
    fmt='[%(asctime)s] %(name)-28s > %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'))
fhandler = logging.FileHandler(f'last.log')
fhandler.setLevel(logging.DEBUG)
fhandler.setFormatter(logging.Formatter(
    fmt='[%(asctime)s] %(name)-38s > %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'))
root_logger.addHandler(fhandler)
root_logger.addHandler(handler)

logger = logging.getLogger(__name__)

# api and database references are needed in many other modules
logger.info('Setting up auth keys...')
api = auth.API()
engine_id = api.me().id
logger.info('Done!')

db = TinyDB('app/database/db.json', indent=4)
logger.info('Database loaded.')

# will generate db if doesn't exist yet
Metadata(db)

# retrieves values from the metadata table in the database
def retrieve(convert_to, tag):
    return convert_to(db.table('metadata').get(doc_id=1)[tag])



class Consts:
    kwords = {
        'gen': 'generate',
        'exe': 'execute',
        'bal': 'balance',
        'lik': 'likes',
        'rtw': 'retweets',
        'snd': 'send',
        'agr': 'agreement',
        'uph': 'upheld',
        'brk': 'broken'
    }
    like_value = retrieve(int, 'like_value')
    like_limit = retrieve(int, 'like_limit')
    retweet_value = retrieve(int, 'retweet_value')
    retweet_limit = retrieve(int, 'retweet_limit')
    tax_rate = retrieve(float, 'tax_rate')
    send_tweets = True

# tweets a message, or displays it to the console if sending tweets is disabled
def emit(message, in_reply_to=None):

    # adds status in response to as "salt" because Twitter doesn't allow duplicate statuses
    if in_reply_to:
        message = f'{message} #{in_reply_to}'

    if Consts.send_tweets:
        api.update_status(
            status=message,
            in_reply_to_status_id=in_reply_to,
            auto_populate_reply_metadata=True
        )

        logger.info('LIVE: ' + message)

    else:
        logger.info('DEBUG: ' + message)