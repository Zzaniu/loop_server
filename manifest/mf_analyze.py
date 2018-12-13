#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Software    : loop_server
# @File        : mf_analyze.py
# @Author      : zaniu (Zzaniu@126.com)
# @Date        : 2018/12/12 20:05
# @Description :
"""分析回执,生成回执上传到mdn文件夹"""
import os
import re

import datetime
import shutil

from utils.sql import Sql
from utils import log

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
            logger.info("分析回执失败，请检，{0!r}".format(getattr(self, 'ClientSeqNo') or getattr(self, 'SeqNo')))
            return
        self.move_file()

    def parse_file(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.content = f.read()
        file_name = os.path.basename(self.file_path)
        assert file_name.lower().startswith(("success", "failed", "receipt")), "回执有误，请检查，回执文件：{0!r}".format(self.file_path)
        if file_name.lower().startswith(("receipt")):
            # 统一编号
            ret = re.search(r"(<JourneyID>(.*?)</JourneyID>)|(<ID>(.*?)</ID>)", self.content, re.S)
            self.SeqNo = (ret.group(2) or ret.group(4)) if ret else ''
            ret = re.search(r'(<Code>(.*?)</Code>)|(<StatementCode>(.*?)</StatementCode>)', self.content)
            self.channel = (ret.group(2) or ret.group(4)) if ret else ''
            ret = re.search(r'(<Text>(.*?)</Text>)|(<StatementDescription>(.*?)</StatementDescription>)', self.content)
            self.message = (ret.group(2) or ret.group(4)) if ret else ''
            self.is_receipt = True
        else:
            self.ClientSeqNo = re.search(r'([K|L][0-9]{18})', file_name).group(1)
            ret = re.search(r'(<ns2:Response>[\s\S]*?<ns2:ID>(.*?)</ns2:ID>)|(<Response><ID>(.*?)</ID>)', self.content)
            self.SeqNo = (ret.group(2) or ret.group(4)) if ret else ''
            ret = re.search(r'(<ns2:StatementCode>(.*?)</ns2:StatementCode>)|(<StatementCode>(.*?)</StatementCode>)', self.content)
            self.channel = (ret.group(2) or ret.group(4)) if ret else ''
            ret = re.search(r'(<ns2:StatementDescription>(.*?)</ns2:StatementDescription>)|(<StatementDescription>(.*?)</StatementDescription>)', self.content)
            self.message = (ret.group(2) or ret.group(4)) if ret else ''

    def update_db(self):
        """更新数据库"""
        _Sql = Sql()

        if self.is_receipt:
            d = {
                "QpNotes": self.message,
                # "QpEntryId": self.entryId,
                "ProcessTime": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
                "DecState": "CR_" + self.channel,
            }
            ret = _Sql.select('ManifestMsg', 'DecState', where={"QpSeqNo": self.SeqNo})
            if ret:
                if 'CR_P' == ret[0][0]:
                    logger.info("跳过状态已经是CR_P的ManifestMsg更新,QpSeqNo:{0!r},msg:{1}".format(self.SeqNo, d))
                    return True
                _Sql.update("ManifestMsg", where={"QpSeqNo": self.SeqNo}, **d)
                logger.info("更新ManifestMsg信息,QpSeqNo:{0!r},msg:{1}".format(self.SeqNo, d))
            else:
                logger.info("更新ManifestMsg信息失败,未找到对应SeqNo, QpSeqNo:{0!r},msg:{1}".format(self.SeqNo, d))
            return True
        else:
            d = {
                "QpSeqNo": self.SeqNo,
                "QpNotes": self.message,
            }
            if d['QpNotes'] and len(d['QpNotes']) > 200:
                d['QpNotes'] = d['QpNotes'][:200]
            d['DecState'] = {'0': 'TS_O&K'}.get(self.channel, 'TS_ERR')
            if _Sql.update("ManifestMsg", where={"ClientSeqNo": self.ClientSeqNo}, **d):
                logger.info("更新ManifestMsg信息,ClientSeqNo:{0!r},msg:{1}".format(getattr(self, "ClientSeqNo"), d))
            else:
                logger.warning("ManifestMsg更新回执失败, 自编号{0!r}不存在或数据库操作失败，请检查".format(self.ClientSeqNo))
                return False
            return True

    def move_file(self):
        """解析过的文件从InBox文件夹移动到InBoxMove文件夹下"""
        str_date = datetime.date.today().strftime('%Y-%m-%d')
        path = self.file_path.split('InBox')[0] + 'InBoxMove'
        date_path = os.path.join(path, str_date)
        if not os.path.exists(date_path):
            os.makedirs(date_path)
        dstfile = os.path.join(date_path, self.file_name)
        shutil.move(self.file_path, dstfile)  # 移动文件
        logger.info("move %s ---> %s" % (self.file_path, dstfile))
