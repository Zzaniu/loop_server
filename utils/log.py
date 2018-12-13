# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/5.
import functools
import logging
import threading

from utils.log_handlers import TimedRotatingFileHandler
from conf import settings


def getlogger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 创建一个handler,用于写入日志文件输出控制台 这种是按照log文件大小
    # fh = RotatingFileHandler(settings.LOG_FILE, maxBytes=settings.LOG_MAX_BYTES,backupCount=settings.LOG_BACKUP_COUNT, encoding="utf-8")

    fh = TimedRotatingFileHandler(
        settings.LOG_FILE, settings.LOG_WHEN, settings.LOG_INTERVAL, settings.LOG_BACKUPCOUNT)

    fh.suffix_time = "%Y-%m-%d"

    ch = logging.StreamHandler()
    # 日志输出格式,并为handler设置formatter
    formatter = logging.Formatter('%(asctime)s-%(name)s- %(funcName)s %(lineno)d-%(levelname)s:%(message)s',
                                  datefmt="%Y-%m-%d %H:%M:%S")

    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # 为logger对象添加handler对象,logger对象可以添加多个fh和ch对象
    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


### Modify by zengwenjun 2018.9.14 ###
def singleton(func):
    """单例装饰器函数"""
    data = {'obj': None}
    _lock = threading.Lock()

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with _lock:
            if data.get('obj') is None:
                data['obj'] = func(*args, **kwargs)
        return data['obj']

    return wrapper