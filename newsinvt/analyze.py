# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/9.

"""分析回执,生成回执上传到mdn文件夹"""
import os
import re

import datetime
import shutil

from utils.sql import Sql
from utils import log
from conf import settings

logger = log.getlogger(__name__)


class ReceiptHandler(object):
    def __init__(self, file_path):
        self.file_path = file_path
        self.is_receipt = False  # 标识该文件是回执还是申报通知
        self.file_name = os.path.basename(self.file_path)


    def exec(self):
        """
        1.打开文件,获取关键信息,更新数据库
        2.生成回执文件
        3.将文件移动到存放回执的文件夹
        4.将回执文件上传到ftp的mdn文件夹
        :return: 
        """
        self.parse_file()
        if not self.update_db():
            logger.info("分析回执失败，请检查日志，ClientSeqNo:{}".format(getattr(self, "ClientSeqNo")))
            return

        self.move_file()

    def parse_file(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.content = f.read()

        file_name = os.path.basename(self.file_path)
        if "Receipt" in file_name:
            # ret = re.search(r"<cusCiqNo>(.*?)</cusCiqNo>", self.content, re.S)
            # self.cusCiqNo = ret.group(1)
            #
            # ret = re.search(r"<noticeDate>(.*?)</noticeDate>", self.content, re.S)
            # self.noticeDate = ret.group(1)
            #
            # ret = re.search(r"<channel>(.*?)</channel>", self.content, re.S)
            # self.channel = ret.group(1)
            #
            # ret = re.search(r"<note>(.*?)</note>", self.content, re.S)
            # self.note = ret.group(1)
            #
            # ret = re.search(r"<dDate>(.*?)</dDate>", self.content, re.S)
            # self.dDate = ret.group(1)

            self.is_receipt = True

        else:
            ret = re.search(r"<DealFlag>(.*?)</DealFlag>", self.content)
            self.DealFlag = ret.group(1) if ret else None

            ret = re.search(r"<CheckInfo>(.*?)</CheckInfo>", self.content, re.S)
            self.ErrorMessage = ret.group(1) if ret else None

            ret = re.search(r"<EtpsPreentNo>(.*?)</EtpsPreentNo>", self.content)
            self.ClientSeqNo = ret.group(1) if ret else None

            ret = re.search(r"<SeqNo>(.*?)</SeqNo>", self.content)
            self.SeqNo = ret.group(1) if ret else None

    def update_db(self):
        """更新数据库"""
        _Sql = Sql()

        if self.is_receipt:
            # d = {
            #     # "QpSeqNo": self.cusCiqNo,
            #     "QpNotes": self.note,
            #     "QpEntryId": self.entryId,
            #     "ProcessTime": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
            #     "DecState": "CR_" + self.channel,
            #
            # }
            # if d["QpEntryId"] is None:
            #     d.pop("DecDate")
            # _Sql.update("DecMsg", where={"QpSeqNo": self.cusCiqNo}, **d)
            # # logger.info("更新DecMsg信息,ClientSeqNo:{},msg:{}".format(getattr(self, "ClientSeqNo"), d))
            #
            # # 插入DecReceipt信息
            # ret = _Sql.select("DecMsg", "DecId,ClientSeqNo", where={"QpSeqNo": self.cusCiqNo})
            # if not ret:
            #     logger.warn(
            #         "插入数据到DecReceipt表时，根据统一编号在DecMsg搜索DecId，ClientSeqNo,未搜到，严重逻辑错误，" +
            #         "说明申报成功后应该将QpSeqNo更新到DecMsg，但此步未做，本DecReceipt信息：{}, 'QpSeqNo': {}".format(d, self.cusCiqNo))
            #     return False
            #
            # DecId, ClientSeqNo = ret[0]
            # d = {
            #     "DecId": DecId,
            #     "SeqNo": self.cusCiqNo,
            #     "ClientSeqNo": ClientSeqNo,
            #     "NoticeDate": self.noticeDate,
            #     "DecState": "CR_" + self.channel,
            #     "Note": self.note,
            #     "DecDate": self.dDate,  # 申报日期
            #     "IEDate": self.dDate,  # 进出口日期
            # }
            # if self.dDate:
            #     pass
            # else:
            #     d.pop("DecDate")
            #     d.pop("IEDate")
            #
            # _Sql.insert("DecReceipt", **d)
            # logger.info("单一窗口：报关单海关回执写入数据库DecReceipt成功:{}".format(d))

            return True

        else:
            d = {
                "QpSeqNo": self.SeqNo,
                "QpNotes": self.ErrorMessage,
                "DecState": "TS_O&K",
            }
            if self.file_name.startswith('Failed'):
                d.pop('QpSeqNo')
            if d['QpNotes'] and len(d['QpNotes']) > 200:
                d['QpNotes'] = d['QpNotes'][:200]
            try:

                _Sql.update("NRelation", where={"ClientSeqNo": getattr(self, "ClientSeqNo")}, **d)
                logger.info("更新DecMsg信息,ClientSeqNo:{},msg:{}".format(getattr(self, "ClientSeqNo"), d))
            except Exception as e:
                logger.warning('更新回执失败，错误信息：{}'.format(e))
                return False

            return True

    def move_file(self):
        """将从ftp下载下来的回执文件从clienttmp_tmp文件夹移动到clienttmp文件夹"""
        dstfile = os.path.join(settings.GOLD_RECEIPT_INOBXMOVE, self.file_name)

        shutil.move(self.file_path, dstfile)  # 移动文件
        logger.info("move %s ---> %s" % (self.file_path, dstfile))
