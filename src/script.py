# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/5.
import time

import datetime
import traceback
from multiprocessing import JoinableQueue
from conf import settings
from license.down_license_process import LicenseProcess
from manifest.mf_process import MFProcess
from manifest.mftp_process import MFTPProcess
from utils import mail
from utils.log import getlogger
from .db_process import DBProcess
from newsinvt.nb_process import NBProcess
from passport.pb_process import PBProcess
from .dftp_process import DFTPProcess
from newsinvt.nftp_process import NFTPProcess
from passport.pftp_process import PFTPProcess
from tminvt.tmb_process import TmBProcess
from tainvt.tab_process import TaBProcess

logger = getlogger(__name__)


class Auto_Run():
    def __init__(self):
        self.sleep_time = settings.TIME
        # self.sleep_time = 20
        self.d_db = None    # 一次申报从数据库获取数据的子进程
        self.d_ftp = None   # 一次申报从ftp获取文件的子进程
        self.n_db = None    # 核注清单从数据库获取数据的子进程
        self.n_ftp = None   # 核注清单从ftp获取文件的子进程
        self.p_db = None    # 核放单从数据库获取数据的子进程
        self.p_ftp = None   # 核放单从ftp获取文件的子进程
        self.tm_db = None
        self.ta_db = None
        self.mf_db = None
        self.mf_ftp = None
        self.license_ftp = None  # 随附单据
        self.run_license_ftp()  # 启动时先执行下载随附单据
        self.run_d_db()     # 启动时先执行一次程序（一次申报）
        self.run_d_ftp()    # 启动时先执行一次程序（一次申报）
        self.run_n_db()     # 启动时先执行一次程序（核注清单）
        # self.run_n_ftp()  # 启动时先执行一次程序（核注清单）
        self.run_p_db()     # 启动时先执行一次程序（核放单）
        self.run_p_ftp()  # 启动时先执行一次程序（核放单）
        self.run_tm_db()
        self.run_ta_db()
        self.run_mf_db()
        self.run_mf_ftp()

        while 1:
            try:
                while 1:
                    time.sleep(self.sleep_time)  # 休息10分钟，判断程序状态
                    self.monitor_process(self.d_db, self.run_d_db, '一次申报db')
                    self.monitor_process(self.d_ftp, self.run_d_ftp, '一次申报ftp')
                    self.monitor_process(self.n_db, self.run_n_db, '核注清单db')
                    # self.monitor_process(self.n_ftp, self.run_n_ftp, '核注清单ftp')
                    self.monitor_process(self.p_db, self.run_p_db, '核放单db')
                    self.monitor_process(self.p_ftp, self.run_p_ftp, '核放单ftp')
                    self.monitor_process(self.license_ftp, self.run_license_ftp, '随附单据ftp')
                    self.monitor_process(self.tm_db, self.run_tm_db, '手册核注清单')
                    self.monitor_process(self.mf_db, self.run_mf_db, '舱单db')
                    self.monitor_process(self.mf_ftp, self.run_mf_ftp, '舱单ftp')

                    # if self.d_db.is_alive():
                    #     logger.info("%s,运行正常" % self.d_db.name)
                    #     # print("现在运行的是:%s,运行正常" % self.p.name)
                    # else:
                    #     logger.error("未检测到db进程运行状态，准备启动程序")
                    #     # print("未检测到程序运行状态，准备启动程序")
                    #     self.run_d_db()
                    #
                    # if self.d_ftp.is_alive():
                    #     logger.info("%s,运行正常" % self.d_ftp.name)
                    #     # print("现在运行的是:%s,运行正常" % self.p.name)
                    # else:
                    #     logger.error("未检测到ftp进程运行状态，准备启动程序")
                    #     # print("未检测到程序运行状态，准备启动程序")
                    #     self.run_d_ftp()
            except Exception as e:
                logger.exception(e)
                logger.error("程序异常,重启")
                mail.send_email(text=str(traceback.format_exc()), subject="ftp或db进程异常终止,请火速前往处理")
                logger.warn("ftp或db进程异常终止,以邮件通知")
                time.sleep(settings.EXCEPTION_WAIT_TIME)

                self.reload_process(self.d_db, self.run_d_db(), '一次申报db')
                self.reload_process(self.d_ftp, self.run_d_ftp(), '一次申报ftp')
                self.reload_process(self.n_db, self.run_n_db(), '核注清单db')
                # self.reload_process(self.n_ftp, self.run_n_ftp(), '一次申报ftp')
                self.reload_process(self.p_db, self.run_p_db(), '核注清单db')
                self.reload_process(self.p_ftp, self.run_p_ftp(), '一次申报ftp')
                self.reload_process(self.license_ftp, self.run_license_ftp(), '随附单据ftp')
                self.reload_process(self.tm_db, self.run_tm_db(), '手册核注清单db')
                self.reload_process(self.mf_db, self.run_mf_db, '舱单db')
                self.reload_process(self.mf_ftp, self.run_mf_ftp, '舱单ftp')

    def reload_process(self, process, run_process, name):
        """
        重启进程
        :param process: 进程
        :param run_process: 进程启动函数
        :param name: 进程名称（一次申报、核注单、核放单）
        :return: None
        """
        try:
            process.terminate()
        except Exception as e:
            logger.exception(e)
            logger.error("{}进程结束发生异常,重启{}进程".format(name, name))
            mail.send_email(text=str(traceback.format_exc()), subject="{}进程结束发生异常,请火速前往处理".format(name))
            logger.warn("{}进程结束发生异常,以邮件通知".format(name))
        finally:
            run_process()

    def monitor_process(self, process, run_process, name):
        """
        监测进程是否正常
        :param process: 进程
        :param run_process: 进程启动函数
        :param name: 进程名称（一次申报、核注单、核放单）
        :return: None
        """
        if process.is_alive():
            logger.info("%s,运行正常" % process.name)
        else:
            logger.error("未检测到{}进程运行状态，准备启动程序".format(name))
            run_process()

    def run_d_db(self):
        """从db获取data"""
        self.d_db = DBProcess()
        self.d_db.start()  # start会自动调用run

    def run_d_ftp(self):
        """从ftp获取file"""
        self.d_ftp = DFTPProcess()
        self.d_ftp.start()  # start会自动调用run

    def run_n_db(self):
        """从db获取data"""
        self.n_db = NBProcess()
        self.n_db.start()  # start会自动调用run

    # def run_n_ftp(self):
    #     """从ftp获取file"""
    #     self.n_ftp = NFTPProcess()
    #     self.n_ftp.start()  # start会自动调用run

    def run_p_db(self):
        """从db获取data"""
        self.p_db = PBProcess()
        self.p_db.start()  # start会自动调用run

    def run_p_ftp(self):
        """从ftp获取file"""
        self.p_ftp = PFTPProcess()
        self.p_ftp.start()  # start会自动调用run

    def run_license_ftp(self):
        """下载随附单据"""
        self.license_ftp = LicenseProcess()
        self.license_ftp.start()  # start会自动调用run

    def run_tm_db(self):
        self.tm_db = TmBProcess()
        self.tm_db.start()

    def run_ta_db(self):
        self.ta_db = TaBProcess()
        self.ta_db.start()

    def run_mf_db(self):
        self.mf_db = MFProcess()
        self.mf_db.start()

    def run_mf_ftp(self):
        self.mf_ftp = MFTPProcess()
        self.mf_ftp.start()
