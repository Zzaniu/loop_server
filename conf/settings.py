# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/5.

import os

DEBUG = True

DB_TASK = True  # 开启DB任务
FTP_TASK = True  # 开启FTP任务

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 主进程检查子进程状态轮询时间,单位:秒
TIME = 120

# 轮询mysql数据库时间间隔,单位秒
LOOP_TIME = 40

# 发生异常后,等待时间,如果此参数设置过小,异常后会非常频繁发送邮件
EXCEPTION_WAIT_TIME = 500

# 工程数据存放文件夹
if DEBUG:
    PROJECT_DATA_DIR = r"C:\ImpPath\DecCus001\OutBox"
else:
    PROJECT_DATA_DIR = r"C:\ImpPath\DecCus001\OutBox"

GOLD_DATA_XML_DIR = r"C:\ImpPath\Sas\GenerateXml"  # 核注清单需要发ZIP格式的，此文件夹用于存放中间XML文件
GOLD_DATA_SEND_DIR = r"C:\ImpPath\Sas\OutBox"
MF_DATA_XML_DIR = r"C:\ImpPath\RMft\GenerateXml"
MF_DATA_SEND_DIR = r"C:\ImpPath\RMft\OutBox"

PROJECT_log=r"d:\test"
# log相关配置
LOG_BASE_DIR = os.path.join(PROJECT_log, "log")

LOG_FILE = os.path.join(LOG_BASE_DIR, "task.log")
LOG_WHEN = "D"  # when 是一个字符串,M: Minutes;H: Hours;D: Days
LOG_INTERVAL = 1  # 是指等待多少个单位when的时间后，Logger会自动重建文件
LOG_BACKUPCOUNT = 0  # 是保留日志个数。默认的0是不会自动删除掉日志。

# 生成的xml文件放的位置
XML_DIR = os.path.join(PROJECT_DATA_DIR)

# 金二生成的xml文件放的位置
GOLD_XML_DIR = os.path.join(GOLD_DATA_XML_DIR)

# 回执文件相关目录
DOWNLOAD_FILE_DIR = r"C:\BTCS"

# 下载的回执
RECEIPT_DIR = os.path.join(DOWNLOAD_FILE_DIR, 'clienttmp')

# 暂存回执,下载的回执先放到暂存文件夹,经过处理后再移动到clienttmp
RECEIPT_TMP_DIR = os.path.join(DOWNLOAD_FILE_DIR, 'clienttmp_tmp')

# 回复QP的回执存放文件夹,由代码生成回执,暂存到clientmdn文件夹,再上传到ftp的clientmdn文件夹
CLIENTMDN_DIR = os.path.join(DOWNLOAD_FILE_DIR, "clientmdn")

for path in [LOG_BASE_DIR, XML_DIR, RECEIPT_DIR, RECEIPT_TMP_DIR, CLIENTMDN_DIR]:
    if not os.path.exists(path):
        os.makedirs(path)

RECEIPT_INOBX = r"C:\ImpPath\DecCus001\InBox"
RECEIPT_INOBX_NEMS = r"C:\ImpPath\Nems\InBox"
RECEIPT_INOBX_NTPS = r"C:\ImpPath\Npts\InBox"
RECEIPT_INOBX_MF = r"C:\ImpPath\RMft\InBox"

# 本地zip单证存放路径
LOCAL_LICENSE_DIR = r"C:\license"
FILE_SERVER_HOST = "111.230.151.179"
FILE_SERVER_USER = "admin"
FILE_SERVER_PASS = "admin"
# 随附单据报文路径
LICENSE_XML_DIR = os.path.join(r"C:\license\DecCus001")
RECEIPT_INOBXMOVE = r"C:\ImpPath\DecCus001\InBoxMove"
SEND_EMAIL = os.environ.get('mailAddr')
EMAIL_PWD = os.environ.get('mailPwd')
GOLD_RECEIPT_INOBX = r"C:\ImpPath\Sas\InBox"
GOLD_RECEIPT_OTHER_INOBX = r"C:\ImpPath\Others\InBox\INV"
GOLD_RECEIPT_INOBXMOVE = r"C:\ImpPath\Sas\InBoxMove"
GOLD_RECEIPT_OTHER_INOBXMOVE = r"C:\ImpPath\Others\InBoxMove"
NPTS_RECEIPT_INOBX = r"C:\ImpPath\Npts\InBox"
NPTS_RECEIPT_INOBXMOVE = r"C:\ImpPath\Npts\InBoxMove"
NEMS_RECEIPT_INOBX = r"C:\ImpPath\Nems\InBox"
NEMS_RECEIPT_INOBXMOVE = r"C:\ImpPath\Nems\InBoxMove"

RE_CONNECT_SQL_TIME = 10    # 数据库重连次数
RE_CONNECT_SQL_WAIT_TIME = 5    # 重连数据库等待时间，s
SERVER = 0
GOLD_8_1 = 1
if SERVER:
    DATABASES = {
        'host': 'gz-cdb-ld4ka6l5.sql.tencentcdb.com',
        'port': 63482,
        'user': 'gmb_bt',
        'password': 'glodtwo!@456',
        'db': 'GMBGTEO',
        'charset': 'utf8',
    }
elif GOLD_8_1:
    DATABASES = {
        'host': '111.230.242.51',
        'port': 3306,
        'user': 'btrProject',
        'password': 'welcome2btr',
        'db': 'goldtwo8.1',
        'charset': 'utf8',
    }
else:
    DATABASES = {
        'host': '111.230.242.51',
        'port': 3306,
        'user': 'btrProject',
        'password': 'welcome2btr',
        'db': 'gmb3',
        'charset': 'utf8',
    }