import json
import logging
import time
from dataclasses import is_dataclass, asdict


class Logger:
    """Utility class for logging messages with timestamps and namespaces."""

    def __init__(self, namespace: str):
        """Initialize the logger for a given namespace.

        Args:
            namespace: The name of the logger namespace (usually the class or module name).
        """
        # Setup logger
        self.ch = logging.StreamHandler()
        self.formatter = logging.Formatter("%(asctime)s %(name)s %(message)s")
        self.formatter.converter = time.localtime
        self.ch.setFormatter(self.formatter)

        self.logger = logging.getLogger(namespace)
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            self.logger.addHandler(self.ch)

    def log(self, msg):
        """Log an info-level message.

        Args:
            msg: The message to log.
        """
        self.logger.info(msg)

    def debug(self, msg, exc_info=False):
        """Log a debug-level message.

        Args:
            msg: The message to log.
            exc_info: Whether to include exception information.
        """
        self.logger.debug(msg, exc_info=exc_info)

    def error(self, msg):
        """Log an error-level message.

        Args:
            msg: The error message to log.
        """
        self.logger.error(msg)

    def log_block(self, msg, title):
        """Log a structured block of data with start/end markers.

        Args:
            msg: The data to log (list or serializable object).
            title: The title of the block.
        """
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

    def log_end(self, title: str) -> None:
        """Log the end marker of a block.

        Args:
            title: The title of the block being closed.
        """
        self.log("********************** %s END **********************" % title)

    def log_start(self, title: str) -> None:
        """Log the start marker of a block.

        Args:
            title: The title of the block being opened.
        """
        self.log("********************** %s START **********************" % title)
