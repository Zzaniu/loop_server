# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/5.

import logging
from logging.handlers import RotatingFileHandler
LOG_FILE = "xxx"

def getlogger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 创建一个handler,用于写入日志文件输出控制台
    fh = RotatingFileHandler(LOG_FILE, maxBytes=50 * 1024 * 1024, backupCount=100, encoding="utf-8")

    ch = logging.StreamHandler()
    # 日志输出格式,并为handler设置formatter
    formatter = logging.Formatter('%(asctime)s-%(name)s-%(levelname)s:%(message)s')

    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # 为logger对象添加handler对象,logger对象可以添加多个fh和ch对象
    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


if __name__ == '__main__':

    logger = getlogger("yang")

    logger.debug('logger debug message')
    logger.info('logger info message')
    logger.warning('logger warning message')
    logger.error('logger error message')
    logger.critical('logger critical message')
