import os
import time
import decimal

import datetime
import traceback
from ftplib import FTP
from multiprocessing import Process
from threading import Thread

from conf import settings
from ftp.ftp_license import FtpConnect, DownLoadFile, zipCompress, move_file
from utils import log, mail, only_win_pdf, sql
from passport import passport as model_passport

from conf.zipfiles import zip_files

logger = log.getlogger(__name__)


class LicenseProcess(Process):
    def __init__(self):
        super().__init__()
        self.name = "DB进程-{}".format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))

    def run(self):
        if not settings.DB_TASK:
            return
        while 1:
            try:
                logger.info('%s start' % self.name)
                self.exec_task()
                logger.info('%s end' % self.name)
                time.sleep(settings.LOOP_TIME)
            except Exception as e:
                logger.exception(e)
                mail.send_email(text=str(traceback.format_exc()), subject="db线程异常,请火速前往处理")
                logger.warn("db线程异常,以邮件通知")
                time.sleep(settings.EXCEPTION_WAIT_TIME)

    def exec_task(self):
        _Sql = sql.Sql()
        license_infos = _Sql.select("LicenseDoc", "ClientSeqNo", where={"DownFlag": 0})
        needed_process_pass = list(set([license_info for license_info in license_infos]))
        logger.info(needed_process_pass)
        threads = []
        for license_info in needed_process_pass:
            # t = Thread(target=self.upload_QP_task, args=(dec_info,))
            t = Thread(target=self.upload_QP_task_pass, args=(license_info,))
            threads.append(t)

        for i in threads:
            i.start()

        for i in threads:
            i.join()

    def upload_QP_task_pass(self, license_info):
        # 取出数据
        _Sql = sql.Sql()
        ClientSeqNo = license_info[0]
        file_name = "{}.zip".format(ClientSeqNo)
        local_license_file = os.path.join(settings.LOCAL_LICENSE_DIR, file_name)

        # 判断本地路径中是否已经下载文件
        # if not os.path.exists(local_license_file):
        logger.info("下载随附单据开始")
        # 下载文件
        ftp = FtpConnect(settings.FILE_SERVER_HOST, settings.FILE_SERVER_USER, settings.FILE_SERVER_PASS)
        DownLoadFile(ftp, local_license_file, file_name)
        logger.info("下载随附单据结束")
        # 下载成功后更新数据库下载标志，与下载时间 where=clientseqno
        downtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _Sql.update("LicenseDoc", where={"ClientSeqNo": ClientSeqNo}, DownTime=downtime, DownFlag=1)
        # _Sql.update("LicenseDoc", where={"id": 1}, DownTime=downtime, DownFlag=1)
        logger.info("更新信息结束")

        # 查看是否产生报文，若没有就等待5秒
        while True:
            if not os.path.exists(os.path.join(settings.LICENSE_XML_DIR, "Dec" + ClientSeqNo + ".xml")):
                time.sleep(10)
                logger.info(ClientSeqNo + "还未生成报文，等待10秒")
            else:
                # 将随附单据的报文拼接到下载文件的zip中
                # 判断本地路径中是否已经下载文件
                zipCompress(settings.LICENSE_XML_DIR, local_license_file, ClientSeqNo)
                logger.info("拼接报文结束")
                # 将数据移动到海关目录
                logger.info("移动到海关目录")
                move_file(settings.LOCAL_LICENSE_DIR, settings.XML_DIR, file_name)
                _Sql.update("LicenseDoc", where={"ClientSeqNo": ClientSeqNo}, DownFlag=2)
                return


if __name__ == '__main__':
    s = LicenseProcess()
    s.run()
