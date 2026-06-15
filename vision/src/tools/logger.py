import multiprocessing
import time
import logging
import sys

class LoggerContent:
    def __init__(self, level : str, message : str):
        self.level = level
        self.message = message

class LogColors:
    RESET = "\033[0m"
    GRAY = "\033[90m"       # DEBUG
    GREEN = "\033[92m"      # INFO
    YELLOW = "\033[93m"     # WARNING
    RED = "\033[91m"        # ERROR
    BOLD_RED = "\033[91;1m" # CRITICAL

class ColoredFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG:    LogColors.GRAY + "[%(asctime)s][%(name)s][%(levelname)s] %(message)s" + LogColors.RESET,
        logging.INFO:     LogColors.GREEN + "[%(asctime)s][%(name)s][%(levelname)s] %(message)s" + LogColors.RESET,
        logging.WARNING:  LogColors.YELLOW + "[%(asctime)s][%(name)s][%(levelname)s] %(message)s" + LogColors.RESET,
        logging.ERROR:    LogColors.RED + "[%(asctime)s][%(name)s][%(levelname)s] %(message)s" + LogColors.RESET,
        logging.CRITICAL: LogColors.BOLD_RED + "[%(asctime)s][%(name)s][%(levelname)s] %(message)s" + LogColors.RESET,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)

def add_log(logging_queue : multiprocessing.Queue, level : str, message : str):
    log_content = LoggerContent(level, message)
    logging_queue.put(log_content)

def logger_process(logging_queue : multiprocessing.Queue):
    logger = logging.getLogger("USV_Client")
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)

    while True:
        try:
            '''
            NOTE: 注意：此处对于 multiprocessing.Queue 的 get 在队列空时会阻塞
            因此其在没有日志消息时会一直等待，直到有新的日志消息被添加到队列中，这期间不占用 CPU 资源
            所以无需在此加入 time.sleep 来降低 CPU 占用率 （这设计挺不错的）
            '''
            log_message: LoggerContent = logging_queue.get()
            level_num = getattr(logging, log_message.level.upper(), logging.INFO)
            logger.log(level_num, log_message.message)
        except Exception:
            continue