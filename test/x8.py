# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/5.

import logging  # 生成一个日志对象
from logging.handlers import RotatingFileHandler
LOG_FILE = "xxxxx.txt"
def initlog():

    logger = logging.getLogger() # 生成一个Handler。logging支持许多Handler，例如FileHandler, SocketHandler, SMTPHandler等，

    # 我由于要写文件就使用了FileHandler。 # LOG_FILE是一个全局变量，它就是一个文件名，如：'crawl.log' LOG_FILE = "/opt/xxx/log/debug.log"
    # hdlr = logging.FileHandler(LOG_FILE,encoding="utf-8") # 生成一个格式器，用于规范日志的输出格式。如果没有这行代码，那么缺省的 # 格式就是："%(message)s"。也就是写日志时，信息是什么日志中就是什么， # 没有日期，没有信息级别等信息。logging支持许多种替换值，详细请看 # Formatter的文档说明。这里有三项：时间，信息级别，日志信息
    hdlr = RotatingFileHandler(LOG_FILE, maxBytes=50*1024*1024, backupCount=100,encoding="utf-8")
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s') # 将格式器设置到处理器上
    hdlr.setFormatter(formatter) # 将处理器加到日志对象上
    logger.addHandler(hdlr) # 设置日志信息输出的级别。logging提供多种级别的日志信息，如：NOTSET, # DEBUG, INFO, WARNING, ERROR, CRITICAL等。每个级别都对应一个数值。 # 如果不执行此句，缺省为30(WARNING)。可以执行：logging.getLevelName # (logger.getEffectiveLevel())来查看缺省的日志级别。日志对象对于不同 # 的级别信息提供不同的函数进行输出，如：info(), error(), debug()等。当 # 写入日志时，小于指定级别的信息将被忽略。因此为了输出想要的日志级别一定 # 要设置好此参数。这里我设为NOTSET（值为0），也就是想输出所有信息
    logger.setLevel(logging.NOTSET)
    return logger


logging1 = initlog()
# for i in range(10):
#     logging1.info(' 注册')
#     logging1.error('error!')
#     logging1.debug('debug')
try:
    3/0
except Exception as e:
    # logger.error(e)
    # import traceback
    # logger.error(e)
    logging1.exception(e)