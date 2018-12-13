import time
import decimal

import datetime
import traceback
from multiprocessing import Process
from threading import Thread

from conf import settings
from utils import log, mail, sql
from newsinvt import newsinvt

logger = log.getlogger(__name__)


class NBProcess(Process):
    def __init__(self):
        super().__init__()
        self.name = "DB进程-{}".format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))

    def run(self):
        if not settings.DB_TASK:
            return
        while 1:
            try:
                logger.info('%s start' % self.name)
                # self.exec_task()
                t = []
                t.append(Thread(target=self.exec_task))
                t.append(Thread(target=self.exec_task_special))
                for i in t:
                    i.start()
                for i in t:
                    i.join()
                logger.info('%s end' % self.name)
                time.sleep(settings.LOOP_TIME)
            except Exception as e:
                logger.exception(e)
                mail.send_email(text=str(traceback.format_exc()), subject="db线程异常,请火速前往处理")
                logger.warn("db线程异常,以邮件通知")
                time.sleep(settings.EXCEPTION_WAIT_TIME)

    def exec_task(self):
        _Sql = sql.Sql()
        dec_infos = _Sql.select("NRelation", "id", "ClientSeqNo", "DecState", "CreateUser",
                                where={"DecState": 'TS_RDY', "DeleteFlag": "0"})

        logger.info(dec_infos)

        # 先全部取出来
        needed_process_decs = [dec_info for dec_info in dec_infos]

        threads = []
        for dec_info in needed_process_decs:
            t = Thread(target=self.upload_QP_task, args=(dec_info,))
            threads.append(t)

        for i in threads:
            i.start()

        for i in threads:
            i.join()

    def exec_task_special(self):
        _Sql = sql.Sql()
        dec_infos = _Sql.select("SpecialNewsInvtMsg", "id", "ClientSeqNo", "DecState", "CreateUser",
                                where={"DecState": 'TS_RDY', "DeleteFlag": "0"})

        logger.info(dec_infos)

        # 先全部取出来
        needed_process_decs = [dec_info for dec_info in dec_infos]

        threads = []
        for dec_info in needed_process_decs:
            t = Thread(target=self.upload_QP_task_special, args=(dec_info,))
            threads.append(t)

        for i in threads:
            i.start()

        for i in threads:
            i.join()

    def upload_QP_task(self, dec_info):
        """
        将报关单提交到QP的任务
        :param dec_info: 报关单信息,是一个元组,内容:("DecId", "ClientSeqNo", "DecState", "CreateUser")
        :return: 
        """
        dec_id = dec_info[0]
        ClientSeqNo = dec_info[1]

        _Sql = sql.Sql()
        dec = {}

        # 获取表头数据
        dec_head_fields = ["id", "BondInvtNo", "SeqNo", "ChgTmsCnt", "PutrecNo", "EtpsInnerInvtNo", "BizopEtpsSccd",
                           "BizopEtpsno", "BizopEtpsNm", "RcvgdEtpsno", "RvsngdEtpsSccd", "RcvgdEtpsNm", "DclEtpsSccd",
                           "DclEtpsno", "DclEtpsNm", "InvtDclTime", "EntpyDclTime", "EntpyNo", "RltInvtNo",
                           "RltPutrecNo", "RltEntryNo", "RltEntryBizopEtpsSccd", "RltEntryBizopEtpsno",
                           "RltEntryBizopEtpsNm", "RltEntryRvsngdEtpsSccd", "RltEntryRcvgdEtpsNo",
                           "RltEntryRcvgdetpsNm", "RltEntryDclEtpsSccd", "RltEntryDclEtpsno", "RltEntryDclEtpsNm",
                           "ImpexpPortcd", "DclPlcCuscd", "ImpexpMarkcd", "MtpckEndprdMarkcd", "SupvModecd",
                           "TrspModecd", "DclcusFlag", "DclcusTypecd", "VrfdedMarkcd", "InvtIochkptStucd", "PrevdTime",
                           "FormalVrfdedTime", "ApplyNo", "ListType", "InputCode", "InputCreditCode", "InputName",
                           "IcCardNo", "InputTime", "ListStat", "CorrEntryDclEtpsSccd", "CorrEntryDclEtpsno",
                           "CorrEntryDclEtpsNm", "DecType", "AddTime", "StshipTrsarvNatcd", "BondInvtTypecd",
                           "EntpyStucd", "PassPortUsedTypecd", "Rmk", "NId", "DataState", "DelcareFlag"]

        dec_head_info = _Sql.select("NemsInvtHeadType", *dec_head_fields, where={"NId": dec_id})

        h = dict(zip(dec_head_fields, dec_head_info[0]))
        h['InvtDclTime'] = h['InvtDclTime'].strftime("%Y%m%d")
        h['EntpyDclTime'] = h['EntpyDclTime'].strftime("%Y%m%d")
        h['PrevdTime'] = h['PrevdTime'].strftime("%Y%m%d")
        h['FormalVrfdedTime'] = h['FormalVrfdedTime'].strftime("%Y%m%d")
        h['InputTime'] = h['InputTime'].strftime("%Y%m%d")
        h['AddTime'] = h['AddTime'].strftime("%Y%m%d")
        # h['EtpsInnerInvtNo'] = ClientSeqNo

        # 数值型 为0.0000时，赋空值
        for i in h:
            if isinstance(h[i], decimal.Decimal) and not h[i]:
                h[i] = ""

        OtherRate = h.get("OtherRate")

        if OtherRate == "":
            pass
        elif OtherRate is None:
            pass
        else:

            OtherRate = decimal.Decimal(OtherRate, decimal.getcontext())
            OtherRate = OtherRate.__round__(5)
            h["OtherRate"] = OtherRate

        PayWay = h.get("PayWay")

        if PayWay:
            PayWay = decimal.Decimal(PayWay, decimal.getcontext())
            PayWay = PayWay.__round__(5)
            h["PayWay"] = PayWay

        h["PDate"] = ""
        dec['DecHead'] = h

        # 获取表体数据
        dec_list_fields = ["id", "SeqNo", "GdsSeqno", "PutrecSeqno", "GdsMtno", "Gdecd", "GdsNm",
                           "GdsSpcfModelDesc", "DclUnitcd", "LawfUnitcd", "SecdLawfUnitcd", "Natcd",
                           "DclUprcAmt",
                           "DclTotalAmt", "UsdStatTotalAmt", "DclCurrcd", "LawfQty", "SecdLawfQty", "WtSfVal",
                           "FstSfVal", "SecdSfVal", "DclQty", "GrossWt", "NetWt", "UseCd", "LvyrlfModecd",
                           "UcnsVerno",
                           "EntryGdsSeqno", "ClyMarkcd", "FlowApplyTbSeqno",
                           "ApplyTbSeqno", "AddTime", "ActlPassQty", "PassPortUsedQty", "Rmk", "FKey"]
        dec_lists_info = _Sql.select("NemsInvtListType", *dec_list_fields,
                                     where={"FKey": dec['DecHead']['id'], 'DeleteFlag': 0})
        dec_list_list = []
        for dec_list_info in dec_lists_info:
            d = dict(zip(dec_list_fields, dec_list_info))
            d['AddTime'] = d['AddTime'].strftime("%Y%m%d")

            for i in d:
                if isinstance(d[i], decimal.Decimal) and not d[i]:
                    d[i] = ""

            WorkUsd = d.get("WorkUsd")
            if WorkUsd == "":
                pass
            elif WorkUsd is None:
                pass
            else:
                WorkUsd = decimal.Decimal(WorkUsd, decimal.getcontext())
                WorkUsd = WorkUsd.__round__(5)
                d["WorkUsd"] = WorkUsd

            dec_list_list.append(d)
        dec['DecLists'] = dec_list_list

        import os
        xml_file_name = os.path.join(settings.GOLD_XML_DIR, "NewsInvt" + ClientSeqNo + ".xml")

        _xml = newsinvt.Xml(xml_file_name, dec)  # 将dec传入xml然后保存到磁盘先,单一窗口类型
        _xml.save()
        from conf.zipfiles import zip_files
        zip_files(xml_file_name)
        logger.info('生成核注清单ZIP报文，自编号{}'.format(ClientSeqNo))
        d = {
            "DecState": 'TS_REQ',
        }
        # 更新状态为“草单，申报提交”
        _Sql.update("NRelation", where={"ClientSeqNo": ClientSeqNo, 'DeleteFlag': 0}, **d)
        logger.info('更新NRelation状态为TS_REQ，自编号{}'.format(ClientSeqNo))

    def upload_QP_task_special(self, dec_info):
        """
        将报关单提交到QP的任务
        :param dec_info: 报关单信息,是一个元组,内容:("DecId", "ClientSeqNo", "DecState", "CreateUser")
        :return:
        """
        dec_id = dec_info[0]
        ClientSeqNo = dec_info[1]

        _Sql = sql.Sql()
        dec = {}

        # 获取表头数据
        dec_head_fields = ["id", "BondInvtNo", "SeqNo", "ChgTmsCnt", "PutrecNo", "EtpsInnerInvtNo", "BizopEtpsSccd",
                           "BizopEtpsno", "BizopEtpsNm", "RcvgdEtpsno", "RvsngdEtpsSccd", "RcvgdEtpsNm", "DclEtpsSccd",
                           "DclEtpsno", "DclEtpsNm", "InvtDclTime", "EntpyDclTime", "EntpyNo", "RltInvtNo",
                           "RltPutrecNo", "RltEntryNo", "RltEntryBizopEtpsSccd", "RltEntryBizopEtpsno",
                           "RltEntryBizopEtpsNm", "RltEntryRvsngdEtpsSccd", "RltEntryRcvgdEtpsNo",
                           "RltEntryRcvgdetpsNm", "RltEntryDclEtpsSccd", "RltEntryDclEtpsno", "RltEntryDclEtpsNm",
                           "ImpexpPortcd", "DclPlcCuscd", "ImpexpMarkcd", "MtpckEndprdMarkcd", "SupvModecd",
                           "TrspModecd", "DclcusFlag", "DclcusTypecd", "VrfdedMarkcd", "InvtIochkptStucd", "PrevdTime",
                           "FormalVrfdedTime", "ApplyNo", "ListType", "InputCode", "InputCreditCode", "InputName",
                           "IcCardNo", "InputTime", "ListStat", "CorrEntryDclEtpsSccd", "CorrEntryDclEtpsno",
                           "CorrEntryDclEtpsNm", "DecType", "AddTime", "StshipTrsarvNatcd", "BondInvtTypecd",
                           "EntpyStucd", "PassPortUsedTypecd", "Rmk", "NId", "DataState", "DelcareFlag"]

        dec_head_info = _Sql.select("SpecialNemsInvtHeadType", *dec_head_fields, where={"NId": dec_id})

        h = dict(zip(dec_head_fields, dec_head_info[0]))
        h['InvtDclTime'] = h['InvtDclTime'].strftime("%Y%m%d")
        h['EntpyDclTime'] = h['EntpyDclTime'].strftime("%Y%m%d")
        h['PrevdTime'] = h['PrevdTime'].strftime("%Y%m%d")
        h['FormalVrfdedTime'] = h['FormalVrfdedTime'].strftime("%Y%m%d")
        h['InputTime'] = h['InputTime'].strftime("%Y%m%d")
        h['AddTime'] = h['AddTime'].strftime("%Y%m%d")
        # h['EtpsInnerInvtNo'] = ClientSeqNo

        # 数值型 为0.0000时，赋空值
        for i in h:
            if isinstance(h[i], decimal.Decimal) and not h[i]:
                h[i] = ""

        OtherRate = h.get("OtherRate")

        if OtherRate == "":
            pass
        elif OtherRate is None:
            pass
        else:

            OtherRate = decimal.Decimal(OtherRate, decimal.getcontext())
            OtherRate = OtherRate.__round__(5)
            h["OtherRate"] = OtherRate

        PayWay = h.get("PayWay")

        if PayWay:
            PayWay = decimal.Decimal(PayWay, decimal.getcontext())
            PayWay = PayWay.__round__(5)
            h["PayWay"] = PayWay

        h["PDate"] = ""
        dec['DecHead'] = h

        # 获取表体数据
        dec_list_fields = ["id", "SeqNo", "GdsSeqno", "PutrecSeqno", "GdsMtno", "Gdecd", "GdsNm",
                           "GdsSpcfModelDesc", "DclUnitcd", "LawfUnitcd", "SecdLawfUnitcd", "Natcd",
                           "DclUprcAmt",
                           "DclTotalAmt", "UsdStatTotalAmt", "DclCurrcd", "LawfQty", "SecdLawfQty", "WtSfVal",
                           "FstSfVal", "SecdSfVal", "DclQty", "GrossWt", "NetWt", "UseCd", "LvyrlfModecd",
                           "UcnsVerno",
                           "EntryGdsSeqno", "ClyMarkcd", "FlowApplyTbSeqno",
                           "ApplyTbSeqno", "AddTime", "ActlPassQty", "PassPortUsedQty", "Rmk", "FKey"]
        dec_lists_info = _Sql.select("SpecialNemsInvtListType", *dec_list_fields,
                                     where={"FKey": dec_id, 'DeleteFlag': 0})
        dec_list_list = []
        for dec_list_info in dec_lists_info:
            d = dict(zip(dec_list_fields, dec_list_info))
            d['AddTime'] = d['AddTime'].strftime("%Y%m%d")

            for i in d:
                if isinstance(d[i], decimal.Decimal) and not d[i]:
                    d[i] = ""

            WorkUsd = d.get("WorkUsd")
            if WorkUsd == "":
                pass
            elif WorkUsd is None:
                pass
            else:
                WorkUsd = decimal.Decimal(WorkUsd, decimal.getcontext())
                WorkUsd = WorkUsd.__round__(5)
                d["WorkUsd"] = WorkUsd

            dec_list_list.append(d)
        dec['DecLists'] = dec_list_list

        import os
        xml_file_name = os.path.join(settings.GOLD_XML_DIR, "SpecialNewsInvt" + ClientSeqNo + ".xml")

        _xml = newsinvt.Xml(xml_file_name, dec)  # 将dec传入xml然后保存到磁盘先,单一窗口类型
        _xml.save()
        from conf.zipfiles import zip_files
        zip_files(xml_file_name)
        logger.info('生成核注清单ZIP报文，自编号{}'.format(ClientSeqNo))
        d = {
            "DecState": 'TS_REQ',
        }
        # 更新状态为“草单，申报提交”
        _Sql.update("SpecialNewsInvtMsg", where={"ClientSeqNo": ClientSeqNo, 'DeleteFlag': 0}, **d)
        logger.info('更新SpecialNewsInvtMsg状态为TS_REQ，自编号{}'.format(ClientSeqNo))
