import logging
from datetime import datetime


def log_time(f):
    def decorator(*args):
        start_time = datetime.now()

        ret = f(*args)

        end_time = datetime.now()
        elapsed_time = end_time - start_time
        logging.info('%s elapsed time: %s', f.__name__, elapsed_time)

        return ret
    return decorator
