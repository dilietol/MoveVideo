import json
import logging
import time
from dataclasses import is_dataclass, asdict

# Setup logger
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(name)s %(message)s")
formatter.converter = time.localtime
ch.setFormatter(formatter)

logger = logging.getLogger("manage-stash")
logger.setLevel(logging.DEBUG)
logger.addHandler(ch)


def log(msg):
    logger.info(msg)


def debug(msg):
    logger.debug(msg)


def log_block(msg, title):
    log_start(title)
    if isinstance(msg, list):
        log(" Number of elements: " + str(len(msg)))
        result = list()
        for elem in msg:
            if is_dataclass(elem):
                result.append(asdict(elem))
            else:
                result.append(elem)
        msg_formatted = json.dumps(result, indent=4)
    else:
        msg_formatted = json.dumps(msg, indent=4)
    logger.info(msg_formatted)
    log_end(title)


def log_end(title):
    log("********************** %s END **********************" % title)


def log_start(title):
    log("********************** %s START **********************" % title)
