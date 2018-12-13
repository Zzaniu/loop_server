# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/8.
import os
import socket
import datetime
import traceback
import ssl
from ftp import ftplib208
# import ftplib208
from utils import log
from conf import settings

logger=log.getlogger(__name__)

class FTP_TLS(ftplib208.FTP_TLS):
    def __init__(self, host='', user='', passwd='', acct='', keyfile=None, certfile=None, timeout=180):
        ftplib208.FTP_TLS.__init__(self, host=host, user=user, passwd=passwd, acct=acct, keyfile=keyfile,
                                   certfile=certfile, timeout=timeout)

    def connect(self, host='', port=0, timeout=-999, source_address=None):
        if host != '':
            self.host = host
        if port > 0:
            self.port = port
        if timeout != -999:
            self.timeout = timeout

        try:
            self.sock = socket.create_connection((self.host, self.port), self.timeout)
            self.af = self.sock.family
            # print ssl._DEFAULT_CIPHERS
            # ssl._DEFAULT_CIPHERS += ':HIGH:!DH:!aNULL'
            # print ssl._DEFAULT_CIPHERS
            # cert_reqs=ssl.CERT_OPTIONAL
            # ciphers="EDH-DSS-DES-CBC3-SHA"
            self.sock = ssl.wrap_socket(self.sock, self.keyfile, self.certfile, cert_reqs=ssl.CERT_NONE,
                                        ssl_version=ssl.PROTOCOL_TLSv1)
            self.file = self.sock.makefile('rb')
            self.welcome = self.getresp()
        except Exception as e:
            traceback.print_exc()
            print(e)

        return self.welcome

    def download(self, remote_file_name, local_file_name):
        with open(local_file_name, 'wb') as fp:
            self.retrbinary('RETR %s' % remote_file_name, fp.write)

    def upload(self, local_file_name, remote_file_name):
        with open(local_file_name, 'rb') as fp:
            self.storbinary('STOR %s' % remote_file_name, fp)


# if __name__ == '__main__':

#先放到tmp文件夹,然后再用线程轮询这个文件夹,生成mdn上报文件,然后再将文件移动到mdn文件夹
# CLIENTTMP = os.path.join(settings.DOWNLOAD_FILE_DIR,"mdn_tmp")
# if not os.path.exists(CLIENTTMP):
#     os.makedirs(CLIENTTMP)


# from ftp.ftplib208 import FTP
# from ftplib import FTP

CLIENTTMP=settings.RECEIPT_TMP_DIR

def ftp_task_tmp():
    host = "as3.szceb.cn"
    port = 39011
    user = 'DXPENT0000016069'
    password = 'K537bkf4'
    ftp = FTP_TLS()

    # host = "39.108.221.252"
    # port = 21
    # user = 'viong'
    # password = '1234yang5678'
    # ftp = FTP()


    ftp.set_debuglevel(2)


    ftp.connect(host, port)
    ftp.login(user, password)


    # ftp.set_pasv(True)
    ftp.set_pasv(True)
    # ftp.prot_p() #ssl下要开启

    # # 切换到serverout目录
    # ftp.cwd("/serverout")
    # print(ftp.pwd())
    #
    # #将serverout目录中的文件移动到clienttmp目录并删除
    # for name in ftp.nlst():
    #     new_name = "/clienttmp/" + name
    #     ftp.rename(name, new_name)  # 这步是移动
    #     logger.info("move {} ---> {}".format(name,new_name))
    # logger.info("移动完成")
    #
    # # 从clienttmp目录中下载文件,并删掉clienttmp目录文件
    # ftp.cwd("/clienttmp")
    # for name in ftp.nlst():
    #     new_file_path = os.path.join(CLIENTTMP, name)
    #     ftp.download(name, new_file_path)
    #     logger.info("download {} ---> {}".format(name, new_file_path))
    #     ftp.delete(name)
    #
    # logger.info("从clienttmp下载,删除完成")

    """将回执上传到mdn"""
    print(ftp.pwd())
    # 将文件上传到/serverout 目录
    # ftp.cwd("/home/viong/serverout")
    ftp.cwd("/serverout")

    local_update_dir = r'D:\dev\data\loop_server\ftp\update'
    for name in os.listdir(local_update_dir):
        file_path = os.path.join(local_update_dir, name)
        cur_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

        names = os.path.basename(file_path).split(".")
        remote_file = names[0].split('@')[0] + "@" + cur_time + "." + names[1]

        # ftp.upload(file_path, remote_file)
        print(file_path)
        print(os.path.exists(file_path))
        with open(file_path, 'rb') as fp:
            ftp.storbinary('STOR %s' % remote_file, fp)


        print("upload {} ---> {}".format(file_path, remote_file))

    logger.info("上传到serverout完成")


    # ftp_task()


def ftp_task():
    # host = "as3.szceb.cn"
    # port = 39011
    # user = 'DXPENT0000016069'
    # password = 'K537bkf4'
    # ftp = FTP_TLS()
    from ftplib import FTP
    host = "39.108.221.252"
    port = 21
    user = 'viong'
    password = '1234yang5678'
    ftp = FTP()
    ftp.set_debuglevel(2)
    ftp.connect(host, port)
    ftp.login(user, password)


    # ftp.set_pasv(True)
    ftp.set_pasv(False) #普通的模式下 这个必须要关闭,不然出问题
    # ftp.prot_p() #ssl下要开启

    # 切换到serverout目录
    # ftp.cwd("/home/viong/serverout")
    # print(ftp.pwd())
    #
    # #将serverout目录中的文件移动到clienttmp目录并删除
    # for name in ftp.nlst():
    #     new_name = "/home/viong/clienttmp/" + name
    #     ftp.rename(name, new_name)  # 这步是移动
    #     logger.info("move {} ---> {}".format(name,new_name))
    # logger.info("移动完成")
    #
    # # 从clienttmp目录中下载文件,并删掉clienttmp目录文件
    # ftp.cwd("/home/viong/clienttmp")
    # for name in ftp.nlst():
    #     new_file_path = os.path.join(CLIENTTMP, name)
    #
    #     with open(new_file_path, 'wb') as fp:
    #         ftp.retrbinary('RETR %s' % name, fp.write)
    #     logger.info("download {} ---> {}".format(name, new_file_path))
    #     ftp.delete(name)
    #
    # logger.info("从clienttmp下载,删除完成")
    #
    # """将回执上传到mdn"""
    # print(ftp.pwd())
    # 将文件上传到/serverout 目录
    ftp.cwd("/home/viong/serverout")

    local_update_dir = r'D:\dev\data\loop_server\ftp\update'
    for name in os.listdir(local_update_dir):
        file_path = os.path.join(local_update_dir, name)
        cur_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

        names = os.path.basename(file_path).split(".")
        remote_file = names[0].split('@')[0] + "@" + cur_time + "." + names[1]

        # ftp.upload(file_path, remote_file)
        with open(file_path, 'rb') as fp:
            ftp.storbinary('STOR %s' % remote_file, fp)


        print("upload {} ---> {}".format(file_path, remote_file))

    logger.info("上传到serverout完成")


    # ftp_task()



