import time
import logging

def sleep_with_details(sleep_time):
    logger = logging.getLogger(__name__)
    for minute in range(sleep_time):
        logger.info(f"Sleeping: {minute + 1} minute(s) out of {sleep_time}")
        time.sleep(60)