#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Software    : loop_server
# @File        : mftp_process.py
# @Author      : zaniu (Zzaniu@126.com)
# @Date        : 2018/12/12 20:05
# @Description :
import os
import time
import re
import datetime
import traceback
from multiprocessing import Process
from threading import Thread

from conf import settings
from utils import log,mail
from manifest.mf_analyze import ReceiptHandler

logger = log.getlogger(__name__)


class MFTPProcess(Process):
    def __init__(self):
        super().__init__()
        self.name = "FTP进程-{}".format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))

    def run(self):
        if settings.FTP_TASK:
            self.analyze_receipt_upload_to_mdn()

    def analyze_receipt_upload_to_mdn(self):
        """分析回执,生成回执上传到mdn文件夹"""
        t = Thread(target=self.thread_analyze_receipt_upload_to_mdn)
        t.start()

    def thread_analyze_receipt_upload_to_mdn(self):
        """分析回执,生成回执上传到mdn文件夹的线程"""
        while 1:
            try:
                logger.info('ftp analyze upload start')
                self.task_analyze_receipt_upload_to_mdn()
                logger.info('ftp analyze upload end')
                time.sleep(settings.LOOP_TIME)
            except Exception as e:
                logger.exception(e)
                mail.send_email(text=str(traceback.format_exc()),subject="分析-生成-上传回执线程异常,请火速前往处理")
                logger.warn("分析-生成-上传回执线程异常,以邮件通知")
                time.sleep(settings.EXCEPTION_WAIT_TIME)

    def task_analyze_receipt_upload_to_mdn(self):
        """分析回执,更新数据库状态"""
        client_tmp_files = os.listdir(settings.RECEIPT_INOBX_MF)
        logger.info("需要处理的文件个数:{}".format(len(client_tmp_files)))
        client_tmp_files = self.handle_files_order(client_tmp_files)
        if len(client_tmp_files) > 0:
            for name in client_tmp_files:
                file_path = os.path.join(settings.RECEIPT_INOBX_MF, name)
                handler = ReceiptHandler(file_path)
                handler.exec()
            logger.info("分析回执,生成回执上传完成")

    def handle_files_order(self,files):
        """将回执按照生成时间dDate排序，需要打开文件获取内容"""
        receipt_files = []
        other_files = []
        for file_name in files:
            if "Receipt" in file_name:
                receipt_files.append(file_name)
            else:
                other_files.append(file_name)
        receipt_files_dict = {}
        for file_name in receipt_files:
            file_path = os.path.join(settings.RECEIPT_INOBX_MF, file_name)
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                ret = re.search(r"<SendTime>(.*?)</SendTime>", content)  # 将回执排序
                if ret:
                    receipt_files_dict[file_path] = datetime.datetime.strptime(ret.group(1), "%Y%m%d%H%M%S%f")
        s = sorted(receipt_files_dict.items(), key=lambda x: x[1])
        b = [i[0] for i in s]
        return other_files+b


if __name__ == "__main__":
    DFTPProcess().start()
