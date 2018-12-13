# !/usr/bin/env python
# coding: utf-8

"""分析回执,生成回执上传到mdn文件夹"""
import copy
import os
import re
import time

import datetime
import shutil

from utils.sql import Sql
from utils import log

logger = log.getlogger(__name__)


class OnlineReceiptHandler(object):
    def __init__(self, file_path):
        self.file_path = file_path
        self.is_receipt = False  # 标识该文件是回执还是申报通知
        self.is_other = False  # 标识该文件是否是other里面的
        self.REC_TM_INV_FLG = False  # 标注是否为加贸手册核注清单
        self.REC_TA_INV_FLG = False  # 标注是否为加贸帐册核注清单
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
            # logger.info("分析回执失败，请检查日志，ClientSeqNo:{}".format(getattr(self, "ClientSeqNo")))
            return

        self.move_file()

    def kindof_receipt(self):
        if re.search('(<INV201>)|(<ns2:INV201>)', self.content):
            self.REC_INV_FLG = True
            return

    def parse_file(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.content = f.read()

        self.kindof_receipt()
        file_name = os.path.basename(self.file_path)
        # Receipt Sas/InBox
        # 这里回执分两种情况，一种是核注清单，一种是核放单.核放单又分审核回执和过卡回执
        if "Receipt_C" in file_name:
            # 说明是回执
            # 统一编号
            if self.REC_INV_FLG:
                # 统一编号
                ret = re.search(r"<etpsPreentNo>(.*?)</etpsPreentNo>", self.content, re.S)
                self.cusCiqNo = ret.group(1) if ret else None
                ret = re.search(r"<manageDate>(.*?)</manageDate>", self.content, re.S)
                _date = ret.group(1) if ret else None
                if _date:
                    self.noticeDate = datetime.datetime.strptime(_date, "%Y-%m-%d %H:%M:%S")
                else:
                    self.noticeDate = None

                ret = re.search(r"<manageResult>(.*?)</manageResult>", self.content, re.S)
                self.channel = ret.group(1) if ret else None
                note_dict = {
                    '1': '通过（已核扣）',
                    '2': '转人工',
                    '3': '退单',
                    '4': '预核扣',
                    '5': '通过（未核扣）',
                }
                self.note = note_dict.get(self.channel, '')
                rets = re.findall(r"<note>(.*?)</note>", self.content, re.S)
                for ret in rets:
                    if ret:
                        self.note += '/r/n' + ret
                    if len(self.note) > 500:
                        self.note = self.note[:500]

                ret = re.search(r"<send_time>(.*?)</send_time>", self.content, re.S)
                self.dDate = ret.group(1) if ret else None
                if self.dDate:
                    self.dDate = datetime.datetime.strptime(self.dDate.split('T')[0], "%Y-%m-%d") if self.dDate else ''

                # 海关编号
                ret = re.search(r"<businessId>(.*?)</businessId>", self.content, re.S)
                self.entryId = ret.group(1) if ret else None

                # 自编号
                ret = re.search(r"<etpsInnerInvtNo>(.*?)</etpsInnerInvtNo>", self.content, re.S)
                self.ClientSeqNo = ret.group(1) if ret else None

                if re.search('Npts', self.file_path):
                    self.REC_TM_INV_FLG = True
                elif re.search('Nems', self.file_path):
                    self.REC_TA_INV_FLG = True
            self.is_receipt = True
        # others
        elif "Receipt_D" in file_name:
            # 核注清单统一编号
            ret = re.search(r"<invPreentNo>(.*?)</invPreentNo>", self.content, re.S)
            self.cusCiqNo = ret.group(1) if ret else None
            ret = re.search(r"<businessId>(.*?)</businessId>", self.content, re.S)
            # 核注清单清单编号
            self.entryId = ret.group(1) if ret else None
            # 一次申报统一编号（关键关联号）
            ret = re.search(r"<entrySeqNo>(.*?)</entrySeqNo>", self.content, re.S)
            self.dec_SeqNo = ret.group(1) if ret else None
            self.is_other = True
            self.ClientSeqNo = None

            if re.search('Npts', self.file_path):
                self.REC_TM_INV_FLG = True
            elif re.search('Nems', self.file_path):
                self.REC_TA_INV_FLG = True

        else:
            ret = re.search(r"<DealFlag>(.*?)</DealFlag>", self.content)
            self.DealFlag = ret.group(1) if ret else None

            ret = re.search(r"<CheckInfo>(.*?)</CheckInfo>", self.content, re.S)
            self.ErrorMessage = ret.group(1) if ret else None

            # ret = re.search('([A-Z]?[0-9]{18})', file_name)
            ret = None
            self.ClientSeqNo = ret.group(1) if ret else None
            if self.ClientSeqNo and self.ClientSeqNo.startswith('F'):
                self.REC_TM_INV_FLG = True  # 这个是加贸核注清单的success回执
            elif self.ClientSeqNo and self.ClientSeqNo.startswith('E'):
                self.REC_TA_INV_FLG = True

            ret = re.search(r"<SeqNo>(.*?)</SeqNo>", self.content)
            self.SeqNo = ret.group(1) if ret else None

    def return_fill_dec(self, _Sql, NId, sqlId, TA_TM_FLAG=True):
        """返填报关单"""
        if self.ClientSeqNo is None:  # 入库成功（Y）的回执无自编号，不返填加贸核注单.考虑到重报的状态，就算海关编号为None也返填
            return
        if TA_TM_FLAG:
            if self.ClientSeqNo.startswith(('E', 'F')):  # 五合一则加贸返填
                DecIds = _Sql.select('OnlineBusinessMsg', 'DecId', where={sqlId: NId, 'DeleteFlag': 0})
            else:
                return

        for decid in DecIds:
            if _Sql.select('DecLicenseDoc', 'id', where={'CertCode': self.entryId, 'DeleteFlag': 0}):
                pass
            else:
                _Sql.insert('DecLicenseDoc', DecId=decid, DocuCode='a', CertCode=self.entryId)

    def updateTMInv(self, _Sql):
        """更新手册receipt回执"""
        d = {
            "QpNotes": self.note,
            "QpEntryId": self.entryId,
            "ProcessTime": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
        }
        _VRFDEDMARKCD = None
        if '1' == self.channel or '5' == self.channel:
            _VRFDEDMARKCD = self.channel
        d.update(DecState="CR_" + self.channel)
        _d = copy.deepcopy(d)
        for k in _d:
            if _d[k] is None:
                d.pop(k)
        ret = _Sql.select('TMMsg', 'id', 'DecState', where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0})
        for _ret in ret:
            _Sql.update('TradeManualInvtHeadType', where={'TMId': _ret[0]}, BONDINVTNO=self.entryId)
            if _VRFDEDMARKCD:
                _Sql.update('TradeManualInvtHeadType', where={'TMId': _ret[0]}, VRFDEDMARKCD=_VRFDEDMARKCD) # 已核扣,未核扣
            if 'Y' == self.channel and re.match('^CR_[1,2,4,5,9]$', _ret[1]):
                logger.info('统一编号为{}的加贸回执跳过更新，信息:{}'.format(self.cusCiqNo, d))
                return True
            else:
                _Sql.update("TMMsg", where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0}, **d)
                if re.match('^CR_[1,2,4,5,9]$', _ret[1]):  # 退单的还是需要反填
                    return True
                self.return_fill_dec(_Sql, _ret[0], 'TMId')  # 返填一次申报

                logger.info('更新统一编号为{}的回执成功，信息:{}'.format(self.cusCiqNo, d))
                return True
        logger.warning('更新回执失败，加贸核注单统一编号{}未存在'.format(self.cusCiqNo))
        return False

    def updateTAInv(self, _Sql):
        """更新帐册receipt回执"""
        d = {
            "QpNotes": self.note,
            "QpEntryId": self.entryId,
            "ProcessTime": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
        }
        _VRFDEDMARKCD = None
        if '1' == self.channel or '5' == self.channel:
            _VRFDEDMARKCD = self.channel
        d.update(DecState="CR_" + self.channel)
        _d = copy.deepcopy(d)
        for k in _d:
            if _d[k] is None:
                d.pop(k)
        ret = _Sql.select('TAMsg', 'id', 'DecState', where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0})
        for _ret in ret:
            _Sql.update('TradeAccountInvtHeadType', where={'TAId': _ret[0]}, BONDINVTNO=self.entryId)
            if _VRFDEDMARKCD:
                _Sql.update('TradeAccountInvtHeadType', where={'TAId': _ret[0]}, VRFDEDMARKCD=_VRFDEDMARKCD)
            if 'Y' == self.channel and re.match('^CR_[1,2,4,5,9]$', _ret[1]):
                logger.info('统一编号为{}的回执跳过更新，信息:{}'.format(self.cusCiqNo, d))
                return True
            else:
                _Sql.update("TAMsg", where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0}, **d)
                if re.match('^CR_[1,2,4,5,9]$', _ret[1]):  # 退单的还是需要反填
                    return True
                self.return_fill_dec(_Sql, _ret[0], 'TAId')  # 返填一次申报
                logger.info('更新统一编号为{}的回执成功，信息:{}'.format(self.cusCiqNo, d))
                return True
        logger.warning('更新回执失败，核注单统一编号{}未存在'.format(self.cusCiqNo))
        return False

    def updateTAInv_REC_D(self, _Sql):
        """加贸账册核注清单更新REC_D回执"""
        TAIds = _Sql.select('TAMsg', 'id', where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0})
        if TAIds:
            for TAId in TAIds:
                DecIds = _Sql.select('OnlineBusinessMsg', 'DecId', where={"TAId": TAId, 'DeleteFlag': 0})
                for decid in DecIds:  # 反填关检关联号至一次申报表头和MSG表
                    ret = _Sql.select('DecMsg', 'QpSeqNo', where={'DecId': decid, 'DeleteFlag': 0})
                    if ret[0][0]:
                        logger.info("关检关联号已存在，核注单统一编号{}".format(self.cusCiqNo))
                        return True
                    else:
                        _Sql.update('DecHead', where={'DecId': decid}, SeqNo=self.dec_SeqNo)
                        _Sql.update('DecMsg', where={'DecId': decid, 'DeleteFlag': 0}, QpSeqNo=self.dec_SeqNo)
        else:
            logger.error("更新关检关联号失败，核注单统一编号{}".format(self.cusCiqNo))
            return False
        d = {
            "QpEntryId": self.entryId,
            "ProcessTime": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
            "DecState": "CR_4",
        }
        ret = _Sql.select('TAMsg', 'id', 'DecState', 'MoreCategory', where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0})
        for _ret in ret:
            if re.match('^CR_\d$', _ret[1]):  # _D是最后回来的，所以不更新了，直接返回
                logger.info('统一编号为{}的保税回执跳过更新，信息:{}'.format(self.cusCiqNo, d))
            else:  # 第一个回来的就是_D的回执，需要更新状态为CR_4，且反填核放单和一次申报关联单证编号
                if re.match('^CR_[Y,Z]$', _ret[1]):
                    pass  # 已经有入库成功的回执，不需要再更新核注单的清单编号
                else:
                    _Sql.update('TradeAccountInvtHeadType', where={'TAId': _ret[0]}, BondInvtNo=self.entryId)
                _Sql.update("TAMsg", where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0}, **d)
                ids = _Sql.select('OnlineBusinessMsg', 'DecId', where={'TAId': _ret[0], 'DeleteFlag': 0})
                for _ids in ids:
                    decid = _ids
                    # 更新报关单随附单证信息
                    if _Sql.select('DecLicenseDoc', 'id', where={'CertCode': self.entryId, 'DeleteFlag': 0}):
                        pass
                    else:
                        _Sql.insert('DecLicenseDoc', DocuCode='a', CertCode=self.entryId, DecId=decid)

        return True

    def updateTMInv_REC_D(self, _Sql):
        """加贸手册核注清单更新REC_D回执"""
        TMIds = _Sql.select('TMMsg', 'id', where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0})
        if TMIds:
            for TMId in TMIds:
                DecIds = _Sql.select('OnlineBusinessMsg', 'DecId', where={"TMId": TMId, 'DeleteFlag': 0})
                for decid in DecIds:  # 反填关检关联号至一次申报表头和MSG表
                    ret = _Sql.select('DecMsg', 'QpSeqNo', where={'DecId': decid, 'DeleteFlag': 0})
                    if ret[0][0]:
                        logger.info("关检关联号已存在，核注单统一编号{}".format(self.cusCiqNo))
                        return True
                    else:
                        _Sql.update('DecHead', where={'DecId': decid}, SeqNo=self.dec_SeqNo)
                        _Sql.update('DecMsg', where={'DecId': decid, 'DeleteFlag': 0}, QpSeqNo=self.dec_SeqNo)
        else:
            logger.error("更新关检关联号失败，核注单统一编号{}".format(self.cusCiqNo))
            return False
        d = {
            "QpEntryId": self.entryId,
            "ProcessTime": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
            "DecState": "CR_4",
        }
        ret = _Sql.select('TMMsg', 'id', 'DecState', where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0})
        for _ret in ret:
            if re.match('^CR_\d$', _ret[1]):  # _D是最后回来的，所以不更新了，直接返回
                logger.info('统一编号为{}的保税回执跳过更新，信息:{}'.format(self.cusCiqNo, d))
            else:  # 第一个回来的就是_D的回执，需要更新状态为CR_4，且反填核放单和一次申报关联单证编号
                if re.match('^CR_[Y,Z]$', _ret[1]):
                    pass  # 已经有入库成功的回执，不需要再更新核注单的清单编号
                else:
                    _Sql.update('TradeManualInvtHeadType', where={'TMId': _ret[0]}, BondInvtNo=self.entryId)
                _Sql.update("TMMsg", where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0}, **d)
                ids = _Sql.select('OnlineBusinessMsg', 'DecId', 'PId', where={'TMId': _ret[0], 'DeleteFlag': 0})
                for _ids in ids:
                    decid, pid = _ids
                    # 更新报关单随附单证信息
                    if _Sql.select('DecLicenseDoc', 'id', where={'CertCode': self.entryId, 'DeleteFlag': 0}):
                        pass
                    else:
                        _Sql.insert('DecLicenseDoc', DocuCode='a', CertCode=self.entryId, DecId=decid)

        return True

    def update_db(self):
        """更新数据库"""
        _Sql = Sql()
        # 核放单：SAS221/SAS223     核注单：INV201
        if self.is_receipt:
            if self.REC_TM_INV_FLG:  # 手册核注清单
                return self.updateTMInv(_Sql)
            elif self.REC_TA_INV_FLG:  # 账册核注清单
                return self.updateTAInv(_Sql)

        elif self.is_other:
            if self.REC_TM_INV_FLG:  # 手册核注清单
                return self.updateTMInv_REC_D(_Sql)
            elif self.REC_TA_INV_FLG:  # 账册核注清单
                return self.updateTAInv_REC_D(_Sql)
        else:
            # success回执
            if '0' == self.DealFlag:
                _DecState = "TS_O&K"
            else:
                _DecState = "TS_ERR"
            d = {
                "QpSeqNo": self.SeqNo,
                "QpNotes": self.ErrorMessage,
                "DecState": _DecState,
            }
            if d['QpSeqNo'] is None:
                d.pop('QpSeqNo')
            if d['QpNotes'] and len(d['QpNotes']) > 200:
                d['QpNotes'] = d['QpNotes'][:200]
            try:
                if self.REC_TM_INV_FLG:
                    TMId = _Sql.select('TMMsg', 'id',
                                       where={"ClientSeqNo": getattr(self, "ClientSeqNo"), 'DeleteFlag': 0})
                    if TMId:
                        _Sql.update("TMMsg", where={"ClientSeqNo": getattr(self, "ClientSeqNo"), 'DeleteFlag': 0}, **d)
                        if self.SeqNo:
                            for _TMId in TMId:
                                _Sql.update("TradeManualInvtHeadType", where={"TMId": _TMId}, SeqNo=self.SeqNo)
                    else:
                        logger.warning("加贸核注清单更新回执失败, 自编号{}不存在".format(self.ClientSeqNo))
                        return False
                elif self.REC_TA_INV_FLG:
                    TAId = _Sql.select('TAMsg', 'id',
                                       where={"ClientSeqNo": getattr(self, "ClientSeqNo"), 'DeleteFlag': 0})
                    if TAId:
                        _Sql.update("TAMsg", where={"ClientSeqNo": getattr(self, "ClientSeqNo"), 'DeleteFlag': 0}, **d)
                        if self.SeqNo:
                            for _TAId in TAId:
                                _Sql.update("TradeAccountInvtHeadType", where={"TAId": _TAId}, SeqNo=self.SeqNo)
                    else:
                        logger.warning("加贸核注清单更新回执失败, 自编号{}不存在".format(self.ClientSeqNo))
                        return False

            except Exception as e:
                logger.warning('更新OnlineBusinessMsg回执失败，错误信息：{}'.format(e))
                return False

            return True

    def move_file(self):
        """将从ftp下载下来的回执文件从clienttmp_tmp文件夹移动到clienttmp文件夹"""
        str_date = time.strftime('%Y-%m-%d', time.localtime(time.time()))
        path = self.file_path.split('InBox')[0] + 'InBoxMove'
        date_path = os.path.join(path, str_date)
        if not os.path.exists(date_path):
            os.makedirs(date_path)
        dstfile = os.path.join(date_path, self.file_name)

        shutil.move(self.file_path, dstfile)  # 移动文件
        logger.info("move %s ---> %s" % (self.file_path, dstfile))

