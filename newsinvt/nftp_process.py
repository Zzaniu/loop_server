# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/9.
import os
import time
import re
import datetime
import traceback
from multiprocessing import Process
from threading import Thread

from conf import settings
from ftp.ftp_util import FTP_TLS
from utils import log,mail
from .analyze import ReceiptHandler

logger = log.getlogger(__name__)


class NFTPProcess(Process):
    def __init__(self):
        super().__init__()
        self.name = "核注清单NFTP进程-{}".format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))

    def run(self):
        if settings.FTP_TASK:
            #self.get_remote_file()
            self.analyze_receipt_upload_to_mdn()

    def get_remote_file(self):
        """从ftp获取文件"""
        t = Thread(target=self.thread_get_remote_file)
        t.start()

    def thread_get_remote_file(self):
        """从ftp获取文件的线程"""
        while 1:
            try:
                logger.info('ftp download start')
                self.task_start()
                logger.info('ftp download end')
                time.sleep(settings.LOOP_TIME)
            except Exception as e:
                logger.exception(e)
                mail.send_email(text=str(traceback.format_exc()), subject="下载回执线程异常,请火速前往处理")
                logger.warn("下载回执线程异常,以邮件通知")
                time.sleep(settings.EXCEPTION_WAIT_TIME)


    def task_start(self):
        """下载任务"""
        ftp = self.get_ftp()

        # 切换到serverout目录
        ftp.cwd("/serverout")
        # ftp.cwd("/home/viong/serverout")
        logger.info("切换到目录:{}".format(ftp.pwd()))

        # 将serverout目录中的文件移动到clienttmp目录(这个移动的动作其实是删除)
        nlst = ftp.nlst()
        logger.info("需要移动的文件个数:{}".format(len(nlst)))
        if len(nlst) > 0:
            for name in nlst:
                new_name = "/clienttmp/" + name
                # new_name = "/home/viong/clienttmp/" + name
                ftp.rename(name, new_name)  # 这步是移动
                logger.info("move {} ---> {}".format(name, new_name))
            logger.info("移动完成")

            # 从clienttmp目录中下载文件,并删掉clienttmp目录文件
            ftp.cwd("/clienttmp")
            # ftp.cwd("/home/viong/clienttmp")
            logger.info("切换到目录:{}".format(ftp.pwd()))

            nlst = ftp.nlst()
            logger.info("需要下载的文件个数:{}".format(len(nlst)))
            if len(nlst) > 0:
                for name in nlst:
                    new_file_path = os.path.join(settings.RECEIPT_TMP_DIR, name)
                    # ftp.download(name, new_file_path)
                    with open(new_file_path, 'wb') as fp:
                        ftp.retrbinary('RETR %s' % name, fp.write)

                    logger.info("download {} ---> {}".format(name, new_file_path))
                    ftp.delete(name)

                logger.info("从clienttmp下载,删除完成")
        ftp.close()

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
        """分析回执,生成回执上传到mdn文件夹的任务"""
        client_tmp_files = os.listdir(settings.GOLD_RECEIPT_INOBX)

        client_tmp_files = self.handle_files_order(client_tmp_files)
        logger.info("需要处理的文件个数:{}".format(len(client_tmp_files)))

        if len(client_tmp_files) > 0:

            for name in client_tmp_files:
                file_path = os.path.join(settings.GOLD_RECEIPT_INOBX, name)
                handler = ReceiptHandler(file_path)
                handler.exec()

            logger.info("分析回执,生成回执上传完成")




    def handle_files_order(self,files):
        """将回执按照生成时间dDate排序，需要打开文件获取内容"""

        receipt_files = []
        other_files = []

        for file_name in files:
            if file_name.startswith("Receipt_N"):
                receipt_files.append(file_name)
            elif file_name.startswith('Successed_N'):
                other_files.append(file_name)

        receipt_files_dict = {}
        for file_name in receipt_files:
            file_path = os.path.join(settings.GOLD_RECEIPT_INOBX, file_name)
            with open(file_path, encoding="utf-8") as f:

                content = f.read()
                ret = re.search(r"<noticeDate>(.*?)</noticeDate>", content)#按照通知时间将回执排序
                if ret:
                    dDate = ret.group(1)
                    receipt_files_dict[file_path] = datetime.datetime.strptime(dDate, "%Y-%m-%d %H:%M:%S")

        s = sorted(receipt_files_dict.items(), key=lambda x: x[1])

        b = [i[0] for i in s]


        return other_files+b




    def get_ftp(self):
        """ """
        #ssl加密连接
        host = "as3.szceb.cn"
        port = 39011
        user = 'DXPENT0000016069'
        password = 'K537bkf4'
        ftp = FTP_TLS(user=user, passwd=password)
        ftp.connect(host, port)
        ftp.login(user, password)
        ftp.set_debuglevel(2)
        # ftp.dir()  # add by yang
        ftp.set_pasv(True)
        ftp.prot_p()
        return ftp


        # #普通连接
        # from ftplib import FTP
        # host = "39.108.221.252"
        # port = 21
        # user = 'viong'
        # password = '1234yang5678'
        # ftp = FTP()
        # # ftp.set_debuglevel(2)
        # ftp.connect(host, port)
        # ftp.login(user, password)
        #
        # # ftp.set_pasv(True)
        # ftp.set_pasv(False)  # 普通的模式下 这个必须要关闭,不然出问题
        # return ftp
