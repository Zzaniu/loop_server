# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/9.

"""分析回执,生成回执上传到mdn文件夹"""
import json
import os
import re
import binascii

import time
import datetime
import shutil

from utils.sql import Sql
from utils import log
from conf import settings
from .mdn_msg import MdnMsg

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
            # logger.info("分析回执失败，请检查日志，ClientSeqNo:%r" % (self.ClientSeqNo))
            return

        self.move_file(settings.RECEIPT_INOBXMOVE)

    def parse_file(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.content = f.read()

        file_name = os.path.basename(self.file_path)

        if "Receipt" in file_name:
            # 统一编号
            ret = re.search(r"<CUS_CIQ_NO>(.*?)</CUS_CIQ_NO>", self.content, re.S)
            self.cusCiqNo = ret.group(1)

            ret = re.search(r"<NOTICE_DATE>(.*?)</NOTICE_DATE>", self.content, re.S)
            self.noticeDate = ret.group(1).replace('T', ' ')
            self.noticeDate = datetime.datetime.strptime(self.noticeDate, "%Y-%m-%d %H:%M:%S")

            ret = re.search(r"<CHANNEL>(.*?)</CHANNEL>", self.content, re.S)
            self.channel = ret.group(1)

            ret = re.search(r"<NOTE>(.*?)</NOTE>", self.content, re.S)
            self.note = ret.group(1)

            ret = re.search(r"<D_DATE>(.*?)</D_DATE>", self.content, re.S)
            self.dDate = ret.group(1)
            self.dDate = datetime.datetime.strptime(self.dDate.split('T')[0], "%Y-%m-%d") if self.dDate else ''
            # 海关编号
            ret = re.search(r"<ENTRY_ID>(.*?)</ENTRY_ID>", self.content, re.S)
            self.entryId = ret.group(1) if ret else None

            self.is_receipt = True

        else:
            if re.search(r"<Root>(.*?)</Root>", self.content, re.S):
                ret = re.search(r"<failInfo>(.*?)</failInfo>", self.content, re.S)
                self.ErrorMessage = ret.group(1) if ret else None
                # ret = re.search(r"<resultFlag>(.*?)</resultFlag>", self.content)
                self.failInfo = '1'
            else:
                ret = re.search(r"<ResponseCode>(.*?)</ResponseCode>", self.content)
                self.failInfo = ret.group(1) if ret else None

                ret = re.search(r"<ErrorMessage>(.*?)</ErrorMessage>", self.content, re.S)
                self.ErrorMessage = ret.group(1) if ret else None

            # ret = re.search(r"<ClientSeqNo>(.*?)</ClientSeqNo>", self.content)
            # self.ClientSeqNo = ret.group(1) if ret else None
            ret = re.search('([A-Z]?[0-9]{18})', file_name)
            self.ClientSeqNo = ret.group(1) if ret else None
            # 统一编号
            ret = re.search(r"<SeqNo>(.*?)</SeqNo>", self.content)
            self.SeqNo = ret.group(1) if ret else None

    def update_more_newsinvt(self, _Sql, DecId, ClientSeqNo, MoreCategory):
        """更新核注清单状态为终审批通过"""
        if 1 == MoreCategory:  # 是四合一的单才去更新核注清单的状态
            if self.channel and ('P' == self.channel.upper() or 'R' == self.channel.upper()):
                # 通过Decmsg的DecId去Relation中找到核注单NRelation的id，然后更新为结关状态
                ret = _Sql.select("Relation", "NId", where={"DecId": DecId})
                if ret:
                    _Sql.update("NRelation", where={"id": ret[0]}, DecState='CR_9')
                    logger.info('已更新自编号为{}的报关单对应的核注清单状态至重审批通过'.format(ClientSeqNo))
                else:
                    raise Exception('错误！未找到四合一单自编号为{}的报关单对应的核注清单'.format(ClientSeqNo))

    def update_db(self):
        """更新数据库"""
        _Sql = Sql()

        if self.is_receipt:
            d = {
                # "QpSeqNo": self.cusCiqNo,
                "QpNotes": self.note,
                "QpEntryId": self.entryId,
                "ProcessTime": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
                "DecState": "CR_" + self.channel,
            }
            ret = _Sql.select('DecMsg', 'DecState', where={"QpSeqNo": self.cusCiqNo})
            if ret:
                is_special = False
                if 'CR_P' == ret[0][0]:
                    return True
                _Sql.update("DecMsg", where={"QpSeqNo": self.cusCiqNo}, **d)
            else:
                ret = _Sql.select('SpecialDecmsg', 'DecState', where={"QpSeqNo": self.cusCiqNo})
                if ret:
                    is_special = True
                    if'CR_P' == ret[0][0]:
                        return True
                    _Sql.update("SpecialDecmsg", where={"QpSeqNo": self.cusCiqNo}, **d)
                else:
                    logger.warn(
                        "根据统一编号在DecMsg/SpecialDecmsg搜索统一编号,未搜到，严重逻辑错误，" +
                        "说明申报成功后应该将QpSeqNo更新到DecMsg，但此步未做，'QpSeqNo': {0!r}".format(self.cusCiqNo))
                    return False
            # logger.info("更新DecMsg信息,ClientSeqNo:{},msg:{}".format(getattr(self, "ClientSeqNo"), d))

            # 插入DecReceipt信息

            ret = _Sql.select("DecMsg", "DecId,ClientSeqNo,MoreCategory", where={"QpSeqNo": self.cusCiqNo})
            if not ret:
                ret = _Sql.select("SpecialDecmsg", "DecId,ClientSeqNo,MoreCategory", where={"QpSeqNo": self.cusCiqNo})
                if not ret:
                    logger.warn(
                        "插入数据到DecReceipt表时，根据统一编号在DecMsg搜索DecId，ClientSeqNo,未搜到，严重逻辑错误，"+
                        "说明申报成功后应该将QpSeqNo更新到DecMsg，但此步未做，本DecReceipt信息：{}, 'QpSeqNo': {}".format(d, self.cusCiqNo))
                    return False
                is_special = True

            DecId, ClientSeqNo, MoreCategory = ret[0]
            d = {
                "DecId": DecId,
                "SeqNo": self.cusCiqNo,
                "ClientSeqNo": ClientSeqNo,
                "NoticeDate": self.noticeDate,
                "DecState": "CR_" + self.channel,
                "Note": self.note,
                "DecDate": self.dDate,  # 申报日期
                "IEDate": self.dDate,   # 进出口日期
            }
            if self.dDate:
                pass
            else:
                d.pop("DecDate")
                d.pop("IEDate")
            if is_special:
                Channel = d.pop('DecState')
                d['Channel'] = Channel
                _Sql.insert("SpecialDecreceipt", **d)
            else:
                _Sql.insert("DecReceipt", **d)
            logger.info("单一窗口：报关单海关回执写入数据库DecReceipt成功:{}".format(d))
            self.update_more_newsinvt(_Sql, DecId, ClientSeqNo, MoreCategory)

            return True
        else:
            d = {
                "QpSeqNo": self.SeqNo,
                "QpNotes": self.ErrorMessage,
            }
            if d['QpSeqNo'] is None:
                d.pop('QpSeqNo')
            if d['QpNotes'] and len(d['QpNotes']) > 200:
                d['QpNotes'] = d['QpNotes'][:200]
            if "0" == self.failInfo:
                d['DecState'] = 'TS_O&K'
            else:
                d['DecState'] = 'TS_ERR'
            if self.ClientSeqNo.upper().startswith('H'):
                print('self.file_name = ', self.file_name)
                decid_tuple = _Sql.select("SpecialDecmsg", 'DecId', where={"ClientSeqNo": getattr(self, "ClientSeqNo")})
                try:
                    if decid_tuple:
                        if _Sql.update("SpecialDecmsg", where={"ClientSeqNo": getattr(self, "ClientSeqNo")}, **d):
                            logger.info("更新SpecialDecmsg信息,ClientSeqNo:{},msg:{}".format(getattr(self, "ClientSeqNo"), d))
                        else:
                            raise Exception('ClientSeqNo:{},msg:{}'.format(getattr(self, "ClientSeqNo"), '数据库操作失败'))
                    else:
                        logger.warning("备案清单更新回执失败, 自编号{}不存在".format(self.ClientSeqNo))
                        return False
                except Exception as e:
                    logger.warning('备案清单{}更新回执失败，错误信息：{}'.format(getattr(self, "ClientSeqNo"), e))
                    return False
            else:
                decid_tuple = _Sql.select("DecMsg", 'DecId', where={"ClientSeqNo": getattr(self, "ClientSeqNo")})
                try:
                    if decid_tuple:
                        if _Sql.update("DecMsg", where={"ClientSeqNo": getattr(self, "ClientSeqNo")}, **d):
                            logger.info("更新DecMsg信息,ClientSeqNo:{},msg:{}".format(getattr(self, "ClientSeqNo"), d))
                        else:
                            raise Exception('ClientSeqNo:{},msg:{}'.format(getattr(self, "ClientSeqNo"), '数据库操作失败'))
                    else:
                        logger.warning("报关单更新回执失败, 自编号{}不存在".format(self.ClientSeqNo))
                        return False
                except Exception as e:
                    logger.warning('报关单{}更新回执失败，错误信息：{}'.format(getattr(self, "ClientSeqNo"), e))
                    return False

            return True


    def move_file(self, path):
        """将从ftp下载下来的回执文件从clienttmp_tmp文件夹移动到clienttmp文件夹"""
        str_date = time.strftime('%Y-%m-%d', time.localtime(time.time()))
        date_path = os.path.join(path, str_date)
        if not os.path.exists(date_path):
            os.makedirs(date_path)
        dstfile = os.path.join(date_path, self.file_name)

        shutil.move(self.file_path, dstfile)  # 移动文件
        logger.info("move %s ---> %s" % (self.file_path, dstfile))
