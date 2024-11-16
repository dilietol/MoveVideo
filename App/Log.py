import json
import logging
import time
from dataclasses import is_dataclass, asdict


class Logger:
    def __init__(self, namespace: str):
        # Setup logger
        self.ch = logging.StreamHandler()
        self.formatter = logging.Formatter("%(asctime)s %(name)s %(message)s")
        self.formatter.converter = time.localtime
        self.ch.setFormatter(self.formatter)

        self.logger = logging.getLogger(namespace)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.ch)

    def log(self, msg):
        self.logger.info(msg)

    def debug(self, msg):
        self.logger.debug(msg)

    def log_block(self, msg, title):
        self.log_start(title)
        if isinstance(msg, list):
            self.log(" Number of elements: " + str(len(msg)))
            result = list()
            for elem in msg:
                if is_dataclass(elem):
                    result.append(asdict(elem))
                else:
                    result.append(elem)
            msg_formatted = json.dumps(result, indent=4)
        else:
            msg_formatted = json.dumps(msg, indent=4)
        self.logger.info(msg_formatted)
        self.log_end(title)

    def log_end(self, title):
        self.log("********************** %s END **********************" % title)

    def log_start(self, title):
        self.log("********************** %s START **********************" % title)
