# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/9.

"""分析回执,生成回执上传到mdn文件夹"""
import copy
import json
import os
import re
import time

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
        self.is_other = False  # 标识该文件是否是other里面的
        self.REC_INV_FLG = False  # 标注是否为核注清单类型的回执
        self.REC_SAS_REVIEW_FLG = False  # 标注是否为核放单审核回执
        self.REC_SAS_CLEARANCE_FLG = False  # 标注是否为核放单过卡回执
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
        if re.search('<SAS221>', self.content):
            self.REC_SAS_REVIEW_FLG = True
            return
        if re.search('<SAS223>', self.content):
            self.REC_SAS_CLEARANCE_FLG = True
            return

    def parsePassPort(self):
        """解析核放单的回执"""
        if self.REC_SAS_REVIEW_FLG or self.REC_SAS_CLEARANCE_FLG:
            # 统一编号
            ret = re.search(r"<etpsPreentNo>(.*?)</etpsPreentNo>", self.content, re.S)
            self.cusCiqNo = ret.group(1) if ret else None
            # 处理结果
            ret = re.search(r"<manageResult>(.*?)</manageResult>", self.content, re.S)
            self.channel = ret.group(1) if ret else None
            note_dict = {
                '1': '通过',
                '2': '转人工',
                '3': '退单',
                'Y': '入库成功',
                'Z': '入库失败',
            }
            self.note = note_dict.get(self.channel)
            rets = re.findall(r"<note>(.*?)</note>", self.content, re.S)
            if self.note:
                for ret in rets:
                    self.note += '/r/n' + ret
                if len(self.note) > 500:
                    self.note = self.note[:500]
            # 海关编号
            ret = re.search(r"<businessId>(.*?)</businessId>", self.content, re.S)
            self.entryId = ret.group(1) if ret else None

            # 221 审核回执
            if self.REC_SAS_REVIEW_FLG:
                note_dict = {
                    '1': '通过',
                    '2': '转人工',
                    '3': '退单',
                    'Y': '入库成功',
                    'Z': '入库失败',
                }
                self.note = note_dict.get(self.channel)
                rets = re.findall(r"<note>(.*?)</note>", self.content, re.S)
                if self.note:
                    for ret in rets:
                        self.note += '/r/n' + ret
                    if len(self.note) > 500:
                        self.note = self.note[:500]
            else:
                # 过卡回执
                note_dict = {
                    '1': '已过卡',
                    '2': '未过卡',
                }
                self.note = note_dict.get(self.channel)

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

            else:
                self.parsePassPort()
            self.is_receipt = True
        # others
        elif "Receipt_D" in file_name:
            # 核注清单统一编号
            ret = re.search(r"<invPreentNo>(.*?)</invPreentNo>", self.content, re.S)
            self.cusCiqNo = ret.group(1) if ret else None
            ret = re.search(r"<businessId>(.*?)</businessId>", self.content, re.S)
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
            if self.ErrorMessage is None:
                ret = re.search(r"<FailInfo>(.*?)</FailInfo>", self.content, re.S)
                self.ErrorMessage = ret.group(1) if ret else None
            # ret = re.search(r"<EtpsPreentNo>(.*?)</EtpsPreentNo>", self.content)
            ret = re.search('([A-Z]?[0-9]{18})', file_name)
            self.ClientSeqNo = ret.group(1) if ret else None
            if self.ClientSeqNo and self.ClientSeqNo.startswith('F'):
                self.REC_TM_INV_FLG = True  # 这个是加贸核注清单的success回执
            elif self.ClientSeqNo and self.ClientSeqNo.startswith('E'):
                self.REC_TA_INV_FLG = True

            ret = re.search(r"<SeqNo>(.*?)</SeqNo>", self.content)
            self.SeqNo = ret.group(1) if ret else None

    def updatePassPort(self, _Sql):
        """更新核放单的回执"""
        if self.REC_SAS_REVIEW_FLG or self.REC_SAS_CLEARANCE_FLG:
            if self.REC_SAS_REVIEW_FLG:
                pass
            else:
                tmp = {
                    '1': '4',
                    '2': '5',
                }
                self.channel = tmp.get(self.channel)
            d = {
                "QpNotes": self.note,
                "QpEntryId": self.entryId,
                "ProcessTime": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
                "DecState": "CR_" + self.channel,
            }
            import copy
            _d = copy.deepcopy(d)
            for k in _d:
                if _d[k] is None:
                    d.pop(k)
            if _Sql.update("PRelation", where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0}, **d):
                return True
            elif _Sql.update("SpecialPassPortMsg", where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0}, **d):
                return True
            else:
                logger.warning('更新回执失败，核注单统一编号{}未存在'.format(self.cusCiqNo))
        return False

    def return_fill_pass(self, _Sql, NId, special_flg):
        """四合一或者五合一，物流账册都返填核放单"""
        if special_flg:
            more_category = _Sql.select('SpecialNewsInvtMsg', 'MoreCategory', where={'id': NId})
            if more_category and 17 == more_category[0][0]:
                PIds = _Sql.select('SpecialFiveMsg', 'PId', where={'NId': NId, 'DeleteFlag': 0})
            else:
                PIds = _Sql.select('SpecialFourMsg', 'PId', where={'NId': NId, 'DeleteFlag': 0})
            for PId in PIds:  # 返填核放单
                _Sql.update('SpecialPassPortHead', where={'PId': PId}, RltNo=self.entryId)
                passports = _Sql.select('SpecialPassPortHead', 'BindTypecd', 'RltTbTypecd', 'id', where={'PId': PId})
                for passport in passports:
                    if 2 == passport[0]:
                        if _Sql.select('SpecialPassPortAcmp', 'id', where={'RltNo': self.entryId, 'PId': PId}):
                            pass
                        else:
                            _Sql.insert('SpecialPassPortAcmp', RltTbTypecd=passport[1], RltNo=self.entryId, PId=PId)
                    logger.info('不是一车一票，不插入核放单关联单证，应返填关联单证编号:{}'.format(self.entryId))
        else:
            more_category = _Sql.select('NRelation', 'MoreCategory', where={'id': NId})
            if more_category and 8 == more_category[0][0]:
                PIds = _Sql.select('Msg', 'PId', where={'NId': NId, 'DeleteFlag': 0})
            else:
                PIds = _Sql.select('Relation', 'PId', where={'NId': NId, 'DeleteFlag': 0})
            for PId in PIds:  # 返填核放单
                _Sql.update('PassPortHead', where={'PId': PId}, RltNo=self.entryId)
                passports = _Sql.select('PassPortHead', 'BindTypecd', 'RltTbTypecd', 'id', where={'PId': PId})
                for passport in passports:
                    if 2 == passport[0]:
                        if _Sql.select('PassPortAcmp', 'id', where={'RltNo': self.entryId, 'Acmp2Head': passport[2]}):
                            pass
                        else:
                            if self.entryId:
                                _Sql.insert('PassPortAcmp', RltTbTypecd=passport[1], RltNo=self.entryId,
                                            Acmp2Head=passport[2])
                    logger.info('不是一车一票，不插入核放单关联单证，应返填关联单证编号:{}'.format(self.entryId))

    def return_fill_tm_or_ta(self, _Sql, NId, special_flg):
        """返填加贸核注单"""
        if special_flg:
            more_category = _Sql.select('SpecialNewsInvtMsg', 'MoreCategory', where={'id': NId})
        else:
            more_category = _Sql.select('NRelation', 'MoreCategory', where={'id': NId})
        if more_category and 8 == more_category[0][0]:
            ids = _Sql.select('Msg', 'TMId', 'TAId', 'DecId', where={'NId': NId, 'DeleteFlag': 0})
        elif more_category and 17 == more_category[0][0]:
            ids = _Sql.select('SpecialFiveMsg', 'TMId', 'TAId', 'SDecId', where={'NId': NId, 'DeleteFlag': 0})
        else:  # 不是五合一不需要返填
            return
        for _ids in ids:
            tmid, taid, decid = _ids
            if special_flg:
                ieflag = _Sql.select('SpecialDechead', 'IEFlag', where={'DecId': decid})
            else:
                ieflag = _Sql.select('DecHead', 'IEFlag', where={'DecId': decid})
            if ieflag and 'E' == ieflag[0][0]:
                if tmid:
                    _Sql.update('TradeManualInvtHeadType', where={'TMId': tmid}, RLTINVTNO=self.entryId)
                elif taid:
                    _Sql.update('TradeAccountInvtHeadType', where={'TAId': taid}, RLTINVTNO=self.entryId)

    def return_fill_news(self, _Sql, TMId, MsgId):
        """返填物流核注单"""
        if 'TAId' == MsgId:
            more_category = _Sql.select('TAMsg', 'MoreCategory', where={'id': TMId})
        elif 'TMId' == MsgId:
            more_category = _Sql.select('TMMsg', 'MoreCategory', where={'id': TMId})
        else:
            raise Exception('MsgId 输入有误')
        if more_category and 8 == more_category[0][0]:
            ids = _Sql.select('Msg', 'NId', 'DecId', where={MsgId: TMId, 'DeleteFlag': 0})
        else:  # 不是五合一不需要返填
            return
        for _ids in ids:
            nid, decid = _ids
            ieflag = _Sql.select('DecHead', 'IEFlag', where={'DecId': decid})
            if ieflag and 'I' == ieflag[0][0]:  # 进口是需要返填物流账册的
                _Sql.update('NemsInvtHeadType', where={'NId': nid}, RltInvtNo=self.entryId)

    def return_fill_dec(self, _Sql, NId, MsgId, special_flg, TA_TM_FLAG=True):
        """返填报关单"""
        if special_flg:
            if TA_TM_FLAG:
                if 'TAId' == MsgId:
                    more_category = _Sql.select('TAMsg', 'MoreCategory', where={'id': NId})
                elif 'TMId' == MsgId:
                    more_category = _Sql.select('TMMsg', 'MoreCategory', where={'id': NId})
                else:
                    raise Exception('MsgId 输入有误')
                if more_category and 13 == more_category[0][0]:  # 五合一则加贸返填
                    DecIds = _Sql.select('SpecialFiveMsg', 'DecId', 'SDecId', where={MsgId: NId, 'DeleteFlag': 0})
                else:
                    return
            else:
                more_category = _Sql.select('SpecialNewsInvtMsg', 'MoreCategory', where={'id': NId})
                if more_category and 13 == more_category[0][0]:
                    return
                else:  # 四合一则物流返填随附单证信息
                    DecIds = _Sql.select('SpecialFourMsg', 'DecId', 'SDecId', where={MsgId: NId, 'DeleteFlag': 0})
            for decid, sdecid in DecIds:
                if decid:
                    if _Sql.select('DecLicenseDoc', 'id', where={'CertCode': self.entryId, 'DeleteFlag': 0}):
                        pass
                    else:
                        if self.entryId and decid:
                            _Sql.insert('DecLicenseDoc', DecId=decid, DocuCode='a', CertCode=self.entryId)
                elif sdecid:
                    if _Sql.select('SpecialDeclicensedoc', 'id', where={'CertCode': self.entryId, 'DeleteFlag': 0}):
                        pass
                    else:
                        if self.entryId and sdecid:
                            _Sql.insert('SpecialDeclicensedoc', DecId=sdecid, DocuCode='a', CertCode=self.entryId)
        else:
            if TA_TM_FLAG:
                if 'TAId' == MsgId:
                    more_category = _Sql.select('TAMsg', 'MoreCategory', where={'id': NId})
                elif 'TMId' == MsgId:
                    more_category = _Sql.select('TMMsg', 'MoreCategory', where={'id': NId})
                else:
                    raise Exception('MsgId 输入有误')
                if more_category and 8 == more_category[0][0]:  # 五合一则加贸返填
                    DecIds = _Sql.select('Msg', 'DecId', where={MsgId: NId, 'DeleteFlag': 0})
                else:
                    return
            else:
                more_category = _Sql.select('NRelation', 'MoreCategory', where={'id': NId})
                if more_category and 8 == more_category[0][0]:
                    return
                else:  # 四合一则物流返填随附单证信息
                    DecIds = _Sql.select('Relation', 'DecId', where={MsgId: NId, 'DeleteFlag': 0})
            for decid in DecIds:
                if _Sql.select('DecLicenseDoc', 'id', where={'CertCode': self.entryId, 'DeleteFlag': 0}):
                    pass
                else:
                    if self.entryId:
                        _Sql.insert('DecLicenseDoc', DecId=decid, DocuCode='a', CertCode=self.entryId)

    def updateNewsInv(self, _Sql):
        """更新物流账册receipt回执"""
        d = {
            "QpNotes": self.note,
            "QpEntryId": self.entryId,
            "ProcessTime": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
        }
        _VrfdedMarkcd = None
        if '1' == self.channel or '5' == self.channel:
            _VrfdedMarkcd = self.channel
        d.update(DecState="CR_" + self.channel)
        _d = copy.deepcopy(d)
        for k in _d:
            if _d[k] is None:
                d.pop(k)
        ret = _Sql.select('NRelation', 'id', 'DecState', where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0})
        special_flg = False
        if not ret:
            ret = _Sql.select('SpecialNewsInvtMsg', 'id', 'DecState', where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0})
            special_flg = True
        for _ret in ret:
            if special_flg:
                _Sql.update('SpecialNemsInvtHeadType', where={'NId': _ret[0]}, BondInvtNo=self.entryId)
                if _VrfdedMarkcd:
                    _Sql.update('SpecialNemsInvtHeadType', where={'NId': _ret[0]}, VrfdedMarkcd=_VrfdedMarkcd)
            else:
                _Sql.update('NemsInvtHeadType', where={'NId': _ret[0]}, BondInvtNo=self.entryId)
                if _VrfdedMarkcd:
                    _Sql.update('NemsInvtHeadType', where={'NId': _ret[0]}, VrfdedMarkcd=_VrfdedMarkcd)
            # 如果是Y的回执，且状态是已经入库成功之后的状态，那么不更新直接返回
            if 'Y' == self.channel and re.match('^CR_[1,2,4,5,9]$', _ret[1]):
                logger.info('统一编号为{}的保税回执跳过更新，信息:{}'.format(self.cusCiqNo, d))
                return True
            else:
                if special_flg:
                    _Sql.update("SpecialNewsInvtMsg", where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0}, **d)
                else:
                    _Sql.update("NRelation", where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0}, **d)
                if re.match('^CR_[1,2,4,5,9]$', _ret[1]) or re.match('^[\w\W]$]', self.channel):  # 退单的还是需要反填
                    return True
                # 加贸与保税都是物流账册返填核放单
                self.return_fill_pass(_Sql, _ret[0], special_flg)
                # 返填加贸核注单
                self.return_fill_tm_or_ta(_Sql, _ret[0], special_flg)
                # 更新报关单
                self.return_fill_dec(_Sql, _ret[0], 'NId', special_flg, TA_TM_FLAG=False)
                self.return_fill_dec_bl(_Sql, _ret[0])
                logger.info('更新统一编号为{}的回执成功，信息:{}'.format(self.cusCiqNo, d))
                return True
        logger.warning('更新回执失败，保税核注单统一编号{}未存在'.format(self.cusCiqNo))
        return False

    def return_fill_dec_bl(self, _Sql, NId):
        """物流账册核注清单的清单编号要返填到一次申报B/L号"""
        ret = _Sql.select('NRelation', 'MoreCategory', where={"id": NId})
        if ret and ret[0][0] == 1:  # 四合一
            decid = _Sql.select('Relation', 'DecId', where={'NId': NId})
            if decid:
                bl = _Sql.select('DecHead', 'BLNo', where={'DecId': decid[0][0]})
                if not bl or not bl[0][0]:
                    _Sql.update('DecHead', where={'DecId': decid[0][0]}, BLNo=self.entryId)
        elif ret and ret[0][0] == 8:  # 五合一
            decid = _Sql.select('Msg', 'DecId', where={'NId': NId})
            if decid:
                bl = _Sql.select('DecHead', 'BLNo', where={'DecId': decid[0][0]})
                if not bl or not bl[0][0]:
                    _Sql.update('DecHead', where={'DecId': decid[0][0]}, BLNo=self.entryId)

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
        ret = _Sql.select('TMMsg', 'id', 'DecState', 'MoreCategory', where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0})
        for _ret in ret:
            _Sql.update('TradeManualInvtHeadType', where={'TMId': _ret[0]}, BONDINVTNO=self.entryId)
            if _VRFDEDMARKCD:
                _Sql.update('TradeManualInvtHeadType', where={'TMId': _ret[0]}, VRFDEDMARKCD=_VRFDEDMARKCD)
            if 'Y' == self.channel and re.match('^CR_[1,2,4,5,9]$', _ret[1]):
                logger.info('统一编号为{}的加贸回执跳过更新，信息:{}'.format(self.cusCiqNo, d))
                return True
            else:
                _Sql.update("TMMsg", where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0}, **d)
                if re.match('^CR_[1,2,4,5,9]$', _ret[1]) and re.match('^[\w\W]$]', self.channel):  # 退单的还是需要反填
                    return True
                if _ret[2] > 11:
                    special_flg = True
                else:
                    special_flg = False
                self.return_fill_dec(_Sql, _ret[0], 'TMId', special_flg)  # 返填一次申报
                self.return_fill_news(_Sql, _ret[0], 'TMId')
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
        ret = _Sql.select('TAMsg', 'id', 'DecState', 'MoreCategory', where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0})
        for _ret in ret:
            _Sql.update('TradeAccountInvtHeadType', where={'TAId': _ret[0]}, BONDINVTNO=self.entryId)
            if _VRFDEDMARKCD:
                _Sql.update('TradeAccountInvtHeadType', where={'TAId': _ret[0]}, VRFDEDMARKCD=_VRFDEDMARKCD)
            if 'Y' == self.channel and re.match('^CR_[1,2,4,5,9]$', _ret[1]):
                logger.info('统一编号为{}的回执跳过更新，信息:{}'.format(self.cusCiqNo, d))
                return True
            else:
                _Sql.update("TAMsg", where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0}, **d)
                if re.match('^CR_[1,2,4,5,9]$', _ret[1]) and re.match('^[\w\W]$]', self.channel):  # 退单的还是需要反填
                    return True
                if _ret[2] > 11:
                    special_flg = True
                else:
                    special_flg = False
                self.return_fill_dec(_Sql, _ret[0], 'TAId', special_flg)  # 返填一次申报
                self.return_fill_news(_Sql, _ret[0], 'TAId')
                logger.info('更新统一编号为{}的回执成功，信息:{}'.format(self.cusCiqNo, d))
                return True
        logger.warning('更新回执失败，核注单统一编号{}未存在'.format(self.cusCiqNo))
        return False

    def updateNewsInv_REC_D(self, _Sql):
        """保税核注清单更新REC_D回执"""
        Nids = _Sql.select('NRelation', 'id', where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0})
        special_flg = False
        if Nids:
            for nid in Nids:
                DecIds = _Sql.select('Relation', 'DecId', where={"NId": nid, 'DeleteFlag': 0})
                for decid in DecIds:  # 反填关检关联号至一次申报表头和MSG表
                    ret = _Sql.select('DecMsg', 'QpSeqNo', where={'DecId': decid, 'DeleteFlag': 0})
                    if ret[0][0]:
                        logger.info("更新关检关联号已存在，核注单统一编号{}".format(self.cusCiqNo))
                        return True
                    else:
                        _Sql.update('DecHead', where={'DecId': decid}, SeqNo=self.dec_SeqNo)
                        _Sql.update('DecMsg', where={'DecId': decid, 'DeleteFlag': 0}, QpSeqNo=self.dec_SeqNo)
                        logger.info("关检关联号，核注单统一编号{},关键关联号{}".format(self.cusCiqNo, self.dec_SeqNo))
            return False
        else:
            Nids = _Sql.select('SpecialNewsInvtMsg', 'id', where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0})
            if Nids:
                special_flg = True
                for nid in Nids:
                    DecIds = _Sql.select('SpecialFourMsg', 'DecId', 'SDecId', where={"NId": nid, 'DeleteFlag': 0})
                    for decid, sdecid in DecIds:  # 反填关检关联号至一次申报表头和MSG表
                        if decid:
                            ret = _Sql.select('DecMsg', 'QpSeqNo', where={'DecId': decid, 'DeleteFlag': 0})
                            if ret and ret[0][0]:
                                logger.info("更新关检关联号已存在，核注单统一编号{}".format(self.cusCiqNo))
                                return True
                            else:
                                _Sql.update('DecHead', where={'DecId': decid}, SeqNo=self.dec_SeqNo)
                                _Sql.update('DecMsg', where={'DecId': decid, 'DeleteFlag': 0},
                                            QpSeqNo=self.dec_SeqNo)
                                logger.info("关检关联号，核注单统一编号{},关键关联号{}".format(self.cusCiqNo, self.dec_SeqNo))
                        elif sdecid:
                            ret = _Sql.select('SpecialDecmsg', 'QpSeqNo', where={'DecId': decid, 'DeleteFlag': 0})
                            if ret and ret[0][0]:
                                logger.info("更新关检关联号已存在，核注单统一编号{}".format(self.cusCiqNo))
                                return True
                            else:
                                _Sql.update('SpecialDechead', where={'DecId': decid}, SeqNo=self.dec_SeqNo)
                                _Sql.update('SpecialDecmsg', where={'DecId': decid, 'DeleteFlag': 0}, QpSeqNo=self.dec_SeqNo)
                                logger.info("关检关联号，核注单统一编号{},关键关联号{}".format(self.cusCiqNo, self.dec_SeqNo))
            else:
                logger.error("更新关检关联号失败，核注单统一编号{}".format(self.cusCiqNo))
                return False
        d = {
            "QpEntryId": self.entryId,
            "ProcessTime": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
            "DecState": "CR_4",
        }
        if special_flg:
            ret = _Sql.select('SpecialNewsInvtMsg', 'id', 'DecState', 'MoreCategory',
                              where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0})
        else:
            ret = _Sql.select('NRelation', 'id', 'DecState', 'MoreCategory',
                              where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0})
        for _ret in ret:
            if re.match('^CR_[1,2,4,5,9]$', _ret[1]):  # _D是最后回来的，所以不更新了，直接返回
                logger.info('统一编号为{}的保税回执跳过更新，信息:{}'.format(self.cusCiqNo, d))
            else:  # 第一个回来的就是_D的回执，需要更新状态为CR_4，且反填核放单和一次申报关联单证编号
                if re.match('^CR_[Y,Z]$', _ret[1]):  # 入库成功还是要返填的，入库失败不返填
                    pass  # 已经有入库成功的回执，不需要再更新核注单的清单编号，还是要返填核放单和一次申报随附单证号
                else:
                    if special_flg:
                        _Sql.update('SpecialNemsInvtHeadType', where={'NId': _ret[0]}, BondInvtNo=self.entryId)
                    else:
                        _Sql.update('NemsInvtHeadType', where={'NId': _ret[0]}, BondInvtNo=self.entryId)
                if special_flg:
                    _Sql.update("SpecialNewsInvtMsg", where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0}, **d)
                    ids = _Sql.select('SpecialFourMsg', 'SDecId', 'PId', where={'NId': _ret[0], 'DeleteFlag': 0})
                else:
                    _Sql.update("NRelation", where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0}, **d)
                    ids = _Sql.select('Relation', 'DecId', 'PId', where={'NId': _ret[0], 'DeleteFlag': 0})
                for _ids in ids:
                    decid, pid = _ids
                    # 更新报关单随附单证信息
                    if special_flg:
                        if _Sql.select('SpecialDeclicensedoc', 'id',
                                       where={'CertCode': self.entryId, 'DeleteFlag': 0, 'DecId': decid}):
                            pass
                        else:  # 没有的话就插入
                            _Sql.insert('SpecialDeclicensedoc', DocuCode='a', CertCode=self.entryId, DecId=decid)
                        _Sql.update('SpecialPassPortHead', where={'PId': pid}, RltNo=self.entryId)
                        passports = _Sql.select('SpecialPassPortHead', 'BindTypecd', 'RltTbTypecd', 'id', where={'PId': pid})
                        if self.entryId:
                            for passport in passports:
                                if 2 == passport[0]:
                                    if _Sql.select('SpecialPassPortAcmp', 'id',
                                                   where={'RltNo': self.entryId, 'PId': pid}):
                                        pass
                                    else:
                                        _Sql.insert('SpecialPassPortAcmp', RltTbTypecd=passport[1], RltNo=self.entryId,
                                                    PId=pid)

                            if 8 == _ret[2]:  # 五合一返填加贸核注清单
                                ids = _Sql.select('SpecialFiveMsg', 'TMId', 'TAId', 'SDecId', where={'NId': _ret[0], 'DeleteFlag': 0})
                                for _ids in ids:
                                    tmid, taid, decid = _ids
                                    ieflag = _Sql.select('SpecialDechead', 'IEFlag', where={'DecId': decid})
                                    if ieflag and 'I' == ieflag[0]:  # 进口是需要返填物流账册的
                                        if tmid:
                                            _Sql.update('TradeManualInvtHeadType', where={'TMId': tmid}, RltInvtNo=self.entryId)
                                        elif taid:
                                            _Sql.update('TradeAccountInvtHeadType', where={'TMId': tmid},
                                                        RltInvtNo=self.entryId)
                    else:
                        if _Sql.select('DecLicenseDoc', 'id',
                                       where={'CertCode': self.entryId, 'DeleteFlag': 0, 'DecId': decid}):
                            pass
                        else:  # 没有的话就插入
                            _Sql.insert('DecLicenseDoc', DocuCode='a', CertCode=self.entryId, DecId=decid)
                        _Sql.update('PassPortHead', where={'PId': pid}, RltNo=self.entryId)
                        passports = _Sql.select('PassPortHead', 'BindTypecd', 'RltTbTypecd', 'id', where={'PId': pid})
                        if self.entryId:
                            for passport in passports:
                                if 2 == passport[0]:
                                    if _Sql.select('PassPortAcmp', 'id',
                                                   where={'RltNo': self.entryId, 'Acmp2Head': passport[2]}):
                                        pass
                                    else:
                                        if self.entryId:
                                            _Sql.insert('PassPortAcmp', RltTbTypecd=passport[1], RltNo=self.entryId,
                                                        Acmp2Head=passport[2])

                            if 8 == _ret[2]:  # 五合一返填加贸核注清单
                                ids = _Sql.select('Msg', 'TMId', 'TAId', 'DecId', where={'NId': _ret[0], 'DeleteFlag': 0})
                                for _ids in ids:
                                    tmid, taid, decid = _ids
                                    ieflag = _Sql.select('DecHead', 'IEFlag', where={'DecId': decid})
                                    if ieflag and 'I' == ieflag[0]:  # 进口是需要返填物流账册的
                                        if tmid:
                                            _Sql.update('TradeManualInvtHeadType', where={'TMId': tmid}, RltInvtNo=self.entryId)
                                        elif taid:
                                            _Sql.update('TradeAccountInvtHeadType', where={'TMId': tmid},
                                                        RltInvtNo=self.entryId)
                        self.return_fill_dec_bl(_Sql, _ret[0])

        return True

    def updateTAInv_REC_D(self, _Sql):
        """保税核注清单更新REC_D回执"""
        TAIds = _Sql.select('TAMsg', 'id', 'MoreCategory', where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0})
        if TAIds:
            for TAId, MoreCategory in TAIds:
                if 8 == MoreCategory:
                    DecIds = _Sql.select('Msg', 'DecId', where={"TAId": TAId, 'DeleteFlag': 0})
                    for decid in DecIds:  # 反填关检关联号至一次申报表头和MSG表
                        ret = _Sql.select('DecMsg', 'QpSeqNo', where={'DecId': decid, 'DeleteFlag': 0})
                        if ret[0][0]:
                            logger.info("关检关联号已存在，核注单统一编号{}".format(self.cusCiqNo))
                            return True
                        else:
                            _Sql.update('DecHead', where={'DecId': decid}, SeqNo=self.dec_SeqNo)
                            _Sql.update('DecMsg', where={'DecId': decid, 'DeleteFlag': 0}, QpSeqNo=self.dec_SeqNo)
                elif 17 == MoreCategory:
                    DecIds = _Sql.select('SpecialFiveMsg', 'DecId', 'SDecId', where={"TAId": TAId, 'DeleteFlag': 0})
                    for decid, sdecid in DecIds:  # 反填关检关联号至一次申报表头和MSG表
                        if decid:
                            ret = _Sql.select('DecMsg', 'QpSeqNo', where={'DecId': decid, 'DeleteFlag': 0})
                            if ret[0][0]:
                                logger.info("关检关联号已存在，核注单统一编号{}".format(self.cusCiqNo))
                                return True
                            else:
                                _Sql.update('DecHead', where={'DecId': decid}, SeqNo=self.dec_SeqNo)
                                _Sql.update('DecMsg', where={'DecId': decid, 'DeleteFlag': 0},
                                            QpSeqNo=self.dec_SeqNo)
                        elif sdecid:
                            ret = _Sql.select('SpecialDecmsg', 'QpSeqNo', where={'DecId': decid, 'DeleteFlag': 0})
                            if ret[0][0]:
                                logger.info("关检关联号已存在，核注单统一编号{}".format(self.cusCiqNo))
                                return True
                            else:
                                _Sql.update('SpecialDechead', where={'DecId': decid}, SeqNo=self.dec_SeqNo)
                                _Sql.update('SpecialDecmsg', where={'DecId': decid, 'DeleteFlag': 0}, QpSeqNo=self.dec_SeqNo)
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
                if 8 == _ret[2]:
                    ids = _Sql.select('Msg', 'DecId', 'PId', where={'TAId': _ret[0], 'DeleteFlag': 0})
                elif 17 == _ret[2]:
                    ids = _Sql.select('SpecialFiveMsg', 'SDecId', 'PId', where={'TAId': _ret[0], 'DeleteFlag': 0})
                for _ids in ids:
                    decid, pid = _ids
                    if self.entryId:
                        # 更新报关单随附单证信息
                        if 8 == _ret[2]:
                            # 更新报关单随附单证信息
                            if _Sql.select('DecLicenseDoc', 'id', where={'CertCode': self.entryId, 'DeleteFlag': 0}):
                                pass
                            else:
                                _Sql.insert('DecLicenseDoc', DocuCode='a', CertCode=self.entryId, DecId=decid)
                            if 8 == _ret[2]:  # 五合一返填物流核注清单
                                ids = _Sql.select('Msg', 'NId', 'DecId', where={'TAId': _ret[0], 'DeleteFlag': 0})
                                for _ids in ids:
                                    nid, decid = _ids
                                    ieflag = _Sql.select('DecHead', 'IEFlag', where={'DecId': decid})
                                    if ieflag and 'I' == ieflag[0]:  # 进口是需要返填物流账册的
                                        _Sql.update('NemsInvtHeadType', where={'NId': nid}, RltInvtNo=self.entryId)
                        elif 17 == _ret[2]:
                            if _Sql.select('SpecialDeclicensedoc', 'id',
                                           where={'CertCode': self.entryId, 'DeleteFlag': 0}):
                                pass
                            else:
                                _Sql.insert('SpecialDeclicensedoc', DocuCode='a', CertCode=self.entryId, DecId=decid)
                            if 8 == _ret[2]:  # 五合一返填物流核注清单
                                ids = _Sql.select('SpecialFiveMsg', 'NId', 'SDecId',
                                                  where={'TAId': _ret[0], 'DeleteFlag': 0})
                                for _ids in ids:
                                    nid, decid = _ids
                                    ieflag = _Sql.select('SpecialDechead', 'IEFlag', where={'DecId': decid})
                                    if ieflag and 'I' == ieflag[0]:  # 进口是需要返填物流账册的
                                        _Sql.update('SpecialNemsInvtHeadType', where={'NId': nid},
                                                    RltInvtNo=self.entryId)
        return True

    def updateTMInv_REC_D(self, _Sql):
        """加贸手册核注清单更新REC_D回执"""
        TMIds = _Sql.select('TMMsg', 'id', 'MoreCategory', where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0})
        # 前海备案清单标志
        is_sdecid_flg = False
        if TMIds:
            for TMId, MoreCategory in TMIds:
                if 8 == MoreCategory:
                    DecIds = _Sql.select('Msg', 'DecId', where={"TMId": TMId, 'DeleteFlag': 0})
                    for decid in DecIds:  # 反填关检关联号至一次申报表头和MSG表
                        ret = _Sql.select('DecMsg', 'QpSeqNo', where={'DecId': decid, 'DeleteFlag': 0})
                        if ret[0][0]:
                            logger.info("关检关联号已存在，核注单统一编号{}".format(self.cusCiqNo))
                            return True
                        else:
                            _Sql.update('DecHead', where={'DecId': decid}, SeqNo=self.dec_SeqNo)
                            _Sql.update('DecMsg', where={'DecId': decid, 'DeleteFlag': 0}, QpSeqNo=self.dec_SeqNo)
                elif 17 == MoreCategory:
                    DecIds = _Sql.select('SpecialFiveMsg', 'DecId', 'SDecId', where={"TMId": TMId, 'DeleteFlag': 0})
                    for decid, sdecid in DecIds:  # 反填关检关联号至一次申报表头和MSG表
                        if decid:
                            ret = _Sql.select('DecMsg', 'QpSeqNo', where={'DecId': decid, 'DeleteFlag': 0})
                            if ret[0][0]:
                                logger.info("关检关联号已存在，核注单统一编号{}".format(self.cusCiqNo))
                                return True
                            else:
                                _Sql.update('DecHead', where={'DecId': decid}, SeqNo=self.dec_SeqNo)
                                _Sql.update('DecMsg', where={'DecId': decid, 'DeleteFlag': 0},
                                            QpSeqNo=self.dec_SeqNo)
                        elif sdecid:
                            is_sdecid_flg = True
                            ret = _Sql.select('SpecialDecmsg', 'QpSeqNo', where={'DecId': decid, 'DeleteFlag': 0})
                            if ret[0][0]:
                                logger.info("关检关联号已存在，核注单统一编号{}".format(self.cusCiqNo))
                                return True
                            else:
                                _Sql.update('SpecialDechead', where={'DecId': decid}, SeqNo=self.dec_SeqNo)
                                _Sql.update('SpecialDecmsg', where={'DecId': decid, 'DeleteFlag': 0}, QpSeqNo=self.dec_SeqNo)
        else:
            logger.error("更新关检关联号失败，核注单统一编号{}".format(self.cusCiqNo))
            return False
        d = {
            "QpEntryId": self.entryId,
            "ProcessTime": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
            "DecState": "CR_4",
        }
        ret = _Sql.select('TMMsg', 'id', 'DecState', 'MoreCategory', where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0})
        for _ret in ret:
            if re.match('^CR_\d$', _ret[1]):  # _D是最后回来的，所以不更新了，直接返回
                logger.info('统一编号为{}的保税回执跳过更新，信息:{}'.format(self.cusCiqNo, d))
            else:  # 第一个回来的就是_D的回执，需要更新状态为CR_4，且反填核放单和一次申报关联单证编号
                if re.match('^CR_[Y,Z]$', _ret[1]):
                    pass  # 已经有入库成功的回执，不需要再更新核注单的清单编号
                else:
                    _Sql.update('TradeManualInvtHeadType', where={'TMId': _ret[0]}, BondInvtNo=self.entryId)
                _Sql.update("TMMsg", where={"QpSeqNo": self.cusCiqNo, 'DeleteFlag': 0}, **d)
                if 8 == _ret[2]:
                    ids = _Sql.select('Msg', 'DecId', 'PId', where={'TMId': _ret[0], 'DeleteFlag': 0})
                elif 17 == _ret[2]:
                    if is_sdecid_flg:
                        ids = _Sql.select('SpecialFiveMsg', 'SDecId', 'PId', where={'TMId': _ret[0], 'DeleteFlag': 0})
                    else:
                        ids = _Sql.select('SpecialFiveMsg', 'DecId', 'PId', where={'TMId': _ret[0], 'DeleteFlag': 0})
                if self.entryId:
                    for _ids in ids:
                        decid, pid = _ids
                        # 更新报关单随附单证信息
                        if 8 == _ret[2] or (17 == _ret[2] and not is_sdecid_flg):
                            if _Sql.select('DecLicenseDoc', 'id', where={'CertCode': self.entryId, 'DeleteFlag': 0}):
                                pass
                            else:
                                _Sql.insert('DecLicenseDoc', DocuCode='a', CertCode=self.entryId, DecId=decid)
                                if 8 == _ret[2]:  # 五合一返填物流核注清单
                                    ids = _Sql.select('Msg', 'NId', 'DecId', where={'TMId': _ret[0], 'DeleteFlag': 0})
                                    for _ids in ids:
                                        nid, decid = _ids
                                        ieflag = _Sql.select('DecHead', 'IEFlag', where={'DecId': decid})
                                        if ieflag and 'I' == ieflag[0]:  # 进口是需要返填物流账册的
                                            _Sql.update('NemsInvtHeadType', where={'NId': nid}, RltInvtNo=self.entryId)
                                elif 17 == _ret[2]:
                                    ids = _Sql.select('SpecialFiveMsg', 'NId', 'DecId',
                                                      where={'TMId': _ret[0], 'DeleteFlag': 0})
                                    for _ids in ids:
                                        nid, decid = _ids
                                        ieflag = _Sql.select('DecHead', 'IEFlag', where={'DecId': decid})
                                        if ieflag and 'I' == ieflag[0]:  # 进口是需要返填物流账册的
                                            _Sql.update('SpecialNemsInvtHeadType', where={'NId': nid},
                                                        RltInvtNo=self.entryId)

                        elif 17 == _ret[2] and is_sdecid_flg:
                            if _Sql.select('SpecialDeclicensedoc', 'id',
                                           where={'CertCode': self.entryId, 'DeleteFlag': 0}):
                                pass
                            else:
                                _Sql.insert('SpecialDeclicensedoc', DocuCode='a', CertCode=self.entryId, DecId=decid)
                                ids = _Sql.select('SpecialFiveMsg', 'NId', 'SDecId',
                                                  where={'TMId': _ret[0], 'DeleteFlag': 0})
                                for _ids in ids:
                                    nid, decid = _ids
                                    ieflag = _Sql.select('SpecialDechead', 'IEFlag', where={'DecId': decid})
                                    if ieflag and 'I' == ieflag[0]:  # 进口是需要返填物流账册的
                                        _Sql.update('SpecialNemsInvtHeadType', where={'NId': nid},
                                                    RltInvtNo=self.entryId)
        return True

    def update_db(self):
        """更新数据库"""
        _Sql = Sql()
        # 核放单：SAS221/SAS223     核注单：INV201
        if self.is_receipt:
            if self.REC_INV_FLG:  # 核注清单
                if self.REC_TM_INV_FLG:  # 手册核注清单
                    return self.updateTMInv(_Sql)
                elif self.REC_TA_INV_FLG:  # 账册核注清单
                    return self.updateTAInv(_Sql)
                else:  # 物流账册核注清单
                    return self.updateNewsInv(_Sql)
            else:  # 核放单
                return self.updatePassPort(_Sql)
        elif self.is_other:
            if self.REC_TM_INV_FLG:  # 手册核注清单
                return self.updateTMInv_REC_D(_Sql)
            elif self.REC_TA_INV_FLG:  # 账册核注清单
                return self.updateTAInv_REC_D(_Sql)
            else:  # 物流账册核注清单
                return self.updateNewsInv_REC_D(_Sql)
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
                "ProcessTime": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
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
                else:
                    if self.file_name.startswith(('Successed_PassPort', 'Failed_PassPort')):
                        Pid = _Sql.select('PRelation', 'id',
                                          where={"ClientSeqNo": getattr(self, "ClientSeqNo"), 'DeleteFlag': 0})
                        if Pid:
                            _Sql.update("PRelation",
                                        where={"ClientSeqNo": getattr(self, "ClientSeqNo"), 'DeleteFlag': 0}, **d)
                        else:
                            logger.warning("核放单更新回执失败, 自编号{}不存在".format(self.ClientSeqNo))
                            return False
                    elif self.file_name.startswith(('Successed_SpecialPassPort', 'Failed_SpecialPassPort')):
                        Pid = _Sql.select('SpecialPassPortMsg', 'id',
                                          where={"ClientSeqNo": getattr(self, "ClientSeqNo"), 'DeleteFlag': 0})
                        if Pid:
                            _Sql.update("SpecialPassPortMsg",
                                        where={"ClientSeqNo": getattr(self, "ClientSeqNo"), 'DeleteFlag': 0}, **d)
                        else:
                            logger.warning("海关特殊监管区域核放单更新回执失败, 自编号{}不存在".format(self.ClientSeqNo))
                            return False
                    elif self.file_name.startswith(('Successed_SpecialNewsInvt', 'Failed_SpecialNewsInvt')):
                        Nid = _Sql.select('SpecialNewsInvtMsg', 'id',
                                          where={"ClientSeqNo": getattr(self, "ClientSeqNo"), 'DeleteFlag': 0})
                        if Nid:
                            _Sql.update("SpecialNewsInvtMsg",
                                        where={"ClientSeqNo": getattr(self, "ClientSeqNo"), 'DeleteFlag': 0}, **d)
                            if self.SeqNo:
                                for NId in Nid:
                                    _Sql.update("SpecialNemsInvtHeadType", where={"NId": NId}, SeqNo=self.SeqNo)
                        else:
                            logger.warning("海关特殊监管区域核注清单更新回执失败, 自编号{}不存在".format(self.ClientSeqNo))
                            return False
                    else:
                        Nid = _Sql.select('NRelation', 'id',
                                          where={"ClientSeqNo": getattr(self, "ClientSeqNo"), 'DeleteFlag': 0})
                        if Nid:
                            _Sql.update("NRelation",
                                        where={"ClientSeqNo": getattr(self, "ClientSeqNo"), 'DeleteFlag': 0}, **d)
                            if self.SeqNo:
                                for NId in Nid:
                                    _Sql.update("NemsInvtHeadType", where={"NId": NId}, SeqNo=self.SeqNo)
                        else:
                            logger.warning("核注清单更新回执失败, 自编号{}不存在".format(self.ClientSeqNo))
                            return False
                    logger.info("更新Msg信息,ClientSeqNo:{},msg:{}".format(getattr(self, "ClientSeqNo"), d))
            except Exception as e:
                logger.warning('更新Msg回执失败，错误信息：{}'.format(e))
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
