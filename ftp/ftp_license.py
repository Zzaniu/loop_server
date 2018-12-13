import os
from zipfile import ZipFile

import shutil

from conf import settings

from ftplib import FTP


# 下载随附单证到本地
from ftp.ftp_util import logger


def DownLoadFile(ftp, local_license_file, file_name):
    try:
        bufsize = 1024  # 设置缓冲块大小
        with open(local_license_file, "wb") as fp:  # 以写模式在本地打开文件
            ftp.retrbinary('RETR ' + file_name, fp.write, bufsize)  # 接收服务器上文件并写入本地文件
            ftp.set_debuglevel(0)  # 关闭调试
            ftp.quit()
    except Exception as err:
        ftp.close()  # 关闭文件
        raise Exception("下载随附单证失败")


# 连接FTP服务器
def FtpConnect(host, username, password):
    ftp = FTP()
    ftp.connect(host=host, port=21)
    ftp.login(username, password)
    return ftp


def addFileIntoZipfile(newDir, fp, clientseqno):
    os.chdir(settings.LICENSE_XML_DIR)
    # xml_path_name = os.path.join(settings.LICENSE_XML_DIR, "Stock201807171108242505.xml")
    # xml_path_name = "Stock201807171108242505.xml"
    xml_path_name = "Dec{}.xml".format(clientseqno)
    logger.info(xml_path_name)

    # 判断是否有报文
    if os.path.exists(xml_path_name):
        fp.write(xml_path_name)
        logger.info("生成报文数据成功")

# 压缩新文件到已有ZIP文件
def zipCompress(newDir, oldZipfile, clientseqno):
    with ZipFile(oldZipfile, mode='a') as fp:
        addFileIntoZipfile(newDir, fp, clientseqno)


def move_file(path, to_path, file_name):
    """将拼接好的文件从clienttmp_tmp文件夹移动到clienttmp文件夹"""
    date_path = os.path.join(path, file_name)
    if not os.path.exists(path):
        os.makedirs(path)

    shutil.move(date_path, to_path)  # 移动文件
    logger.info("move %s ---> %s" % (date_path, to_path))
