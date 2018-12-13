# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/5.
import os
import time
import decimal

import datetime
import traceback
from multiprocessing import Process
from threading import Thread

from conf import settings
from utils import log, mail, xml, sw_xml, only_win, only_win_pdf, sql

logger = log.getlogger(__name__)


class DBProcess(Process):
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
        dec_infos = _Sql.select("DecMsg", "DecId", "ClientSeqNo", "DecState", "CreateUser", 'MoreCategory',
                                where={"DecState": 'TS_RDY', "DeleteFlag": "0"})
        # Sql().select("Decmsg", "*", where={"ClientSeqNo": '201801100950223990', "DeleteFlag": "0"})

        logger.info(dec_infos)

        # 找出需要处理的报关单的id
        # needed_process_dec_ids = [dec_info for dec_info in dec_infos if dec_info[2] == "TS_RDY" ]
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
        dec_infos = _Sql.select("SpecialDecmsg", "DecId", "ClientSeqNo", "DecState", "CreateUser", 'MoreCategory',
                                where={"DecState": 'TS_RDY', "DeleteFlag": "0"})
        # Sql().select("Decmsg", "*", where={"ClientSeqNo": '201801100950223990', "DeleteFlag": "0"})

        logger.info(dec_infos)

        # 找出需要处理的报关单的id
        # needed_process_dec_ids = [dec_info for dec_info in dec_infos if dec_info[2] == "TS_RDY" ]
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
        MoreCategory = dec_info[4]

        _Sql = sql.Sql()
        dec = {}

        # 获取表头数据
        dec_head_fields = ["DecHeadId", "DecId", "SeqNo", "IEFlag", "AgentCode", "AgentName", "ApprNo",
                           "BillNo", "ContrNo", "CustomMaster", "CutMode", "DistinatePort",
                           "FeeCurr", "FeeMark", "FeeRate", "GrossWet", "IEDate", "IEPort",
                           "InsurCurr", "InsurMark", "InsurRate", "LicenseNo", "ManualNo",
                           "NetWt", "Notes", "OtherCurr", "OtherMark", "OtherRate", "OwnerCode",
                           "OwnerName", "PackNo", "TradeCode", "TradeCountry",
                           "TradeMode", "TradeName", "TrafMode", "TrafName", "TransMode", "WrapType",
                           "EntryId", "PreEntryId", "EdiId", "Risk", "CopName", "CopCode",
                           "EntryType", "PDate", "TypistNo", "InputerName", "PartenerID", "TgdNo",
                           "DataSource", "DeclTrnRel", "ChkSurety", "BillType", "AgentCodeScc", "OwnerCodeScc",
                           "TradeCoScc", "CopCodeScc", "PromiseItmes", "TradeAreaCode", 'MarkNo', 'DespPortCode',
                           'EntyPortCode', 'GoodsPlace', 'OverseasConsignorEname', 'OverseasConsignorCode',
                           'OverseasConsigneeEname', 'OverseasConsigneeCode', 'CorrelationNo', 'SpecDeclFlag',
                           'TradeCiqCode', 'OwnerCiqCode', 'DeclCiqCode', 'OrigBoxFlag', 'CorrelationReasonFlag',
                           'InspOrgCode', 'PurpOrgCode', 'BLNo', 'TaxAaminMark', 'CheckFlow', 'OrgCode', 'VsaOrgCode',
                           'DespDate', 'Type']

        dec_head_info = _Sql.select("DecHead", *dec_head_fields, where={"DecId": dec_id})

        h = dict(zip(dec_head_fields, dec_head_info[0]))

        # 数值型 为0.0000时，赋空值
        for i in h:
            if isinstance(h[i], decimal.Decimal) and not h[i]:
                h[i] = ""

        OtherRate = h.get("OtherRate")
        #
        # OtherRate = float(OtherRate)

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

        # if not h["PayWay"]:
        # h["PayWay"]=1  #测试用
        ieflag = h['IEFlag']
        if 'I' == ieflag:
            if not h['IEDate']:
                h['IEDate'] = datetime.datetime.now().strftime("%Y%m%d")
                # 需要添加到数据库
                _Sql.update("DecHead", where={"DecId": dec_id}, IEDate=h['IEDate'])
        dec['DecHead'] = h

        # 获取表体数据
        dec_list_fields = ["id", "DecId", "GNo", "ClassMark", "CodeTs", "ContrItem",
                           "DeclPrice", "DutyMode", "Factor", "GModel", "GName", "OriginCountry",
                           "TradeCurr", "DeclTotal", "GQty", "FirstQty", "SecondQty", "GUnit",
                           "FirstUnit", "SecondUnit", "UseTo", "WorkUsd", "ExgNo", "ExgVersion",
                           "DestinationCountry", 'DistrictCode', 'CiqCode', 'OrigPlaceCode', 'CiqName', 'GoodsAttr',
                           'GoodsSpec', 'Purpose', 'NoDangFlag', 'UnCode', 'DangName', 'DangPackType', 'DangPackSpec',
                           'DestCode', 'Stuff', 'ProdValidDt', 'ProdQgp', 'EngManEntCnm', 'GoodsModel',
                           'GoodsBrand', 'ProduceDate', 'ProdBatchNo']
        dec_lists_info = _Sql.select("DecList", *dec_list_fields, where={"DecId": dec_id, 'DeleteFlag': 0})
        dec_list_list = []
        dec['DecGoodsLimits'] = {}
        dec['DecGoodsLimitVins'] = {}
        for dec_list_info in dec_lists_info:
            d = dict(zip(dec_list_fields, dec_list_info))

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

            # 取许可证信息
            dec_goodslimit_fields = ['DecListId', 'GoodsNo', 'LicTypeCode', 'LicenceNo', 'LicWrtofDetailNo',
                                     'LicWrtofQty']
            dec_goodslimitvin_fields = ['DecListId', 'LicenceNo', 'LicTypeCode', 'VinNo', 'BillLadDate', 'QualityQgp',
                                        'MotorNo', 'VinCode', 'ChassisNo', 'InvoiceNum', 'ProdCnnm', 'ProdEnnm',
                                        'ModelEn', 'PricePerUnit']

            dec_goodslimit_infos = _Sql.select("DecGoodsLimit", *dec_goodslimit_fields,
                                               where={"DecListId": d['id'], 'DeleteFlag': 0})
            for dec_goodslimit_info in dec_goodslimit_infos:
                goodslimit_dict = dict(zip(dec_goodslimit_fields, dec_goodslimit_info))
                dec['DecGoodsLimits'][d['id']] = goodslimit_dict

            dec_goodslimitvin_infos = _Sql.select("DecGoodsLimitVin", *dec_goodslimitvin_fields,
                                                  where={"DecListId": d['id'], 'DeleteFlag': 0})
            for dec_goodslimitvin_info in dec_goodslimitvin_infos:
                goodslimitvin_dict = dict(zip(dec_goodslimitvin_fields, dec_goodslimitvin_info))
                dec['DecGoodsLimitVins'][d['id']] = goodslimitvin_dict

        dec['DecLists'] = dec_list_list

        # 获取集装箱数据
        dec_container_fields = ["ContainerId", "ContainerMd", "GoodsNo", 'LclFlag', 'ContainerWt']
        dec_containers_info = _Sql.select("DecContainer", *dec_container_fields,
                                          where={"DecId": dec_id, 'DeleteFlag': 0})
        dec_container_list = []
        for dec_container_info in dec_containers_info:
            dec_container_list.append(dict(zip(dec_container_fields, dec_container_info)))
        dec['DecContainers'] = dec_container_list

        # 获取单证数据
        dec_license_docu_fields = ["DocuCode", "CertCode"]
        dec_license_docus_info = _Sql.select("DecLicenseDoc", *dec_license_docu_fields,
                                             where={"DecId": dec_id, 'DeleteFlag': 0})
        dec_license_docu_list = []
        for dec_license_docu_info in dec_license_docus_info:
            dec_license_docu_list.append(dict(zip(dec_license_docu_fields, dec_license_docu_info)))
        dec['DecLicenseDocus'] = dec_license_docu_list

        # 获取自由文本信息
        dec_free_txt_fields = ["BonNo", "CusFie", 'RelId', 'RelManNo', 'VoyNo']
        dec_free_txt_infos = _Sql.select("DecFreeTxt", *dec_free_txt_fields, where={"DecId": dec_id, 'DeleteFlag': 0})
        dec_free_txt_info_list = []
        for dec_free_txt_info in dec_free_txt_infos:
            dec_free_txt_info_list.append(dict(zip(dec_free_txt_fields, dec_free_txt_info)))
        dec['DecFreeTxt'] = dec_free_txt_info_list

        # 获取申请单证信息
        dec_requestcert_fields = ['AppCertCode', 'ApplOri', 'ApplCopyQuan']
        dec_requestcert_infos = _Sql.select('DecRequestCert', *dec_requestcert_fields,
                                            where={'DecId': dec_id, 'DeleteFlag': 0})
        dec_requestcert_info_list = []
        for dec_requestcert_info in dec_requestcert_infos:
            dec_requestcert_info_list.append(dict(zip(dec_requestcert_fields, dec_requestcert_info)))
        dec['DecRequestCert'] = dec_requestcert_info_list

        # 获取企业资质信息表
        dec_coplimit_fields = ['EntQualifNo', 'EntQualifTypeCode']
        dec_coplimit_infos = _Sql.select('DecCopLimit', *dec_coplimit_fields, where={'DecId': dec_id, 'DeleteFlag': 0})
        dec_coplimit_info_list = []
        for dec_coplimit_info in dec_coplimit_infos:
            dec_coplimit_info_list.append(dict(zip(dec_coplimit_fields, dec_coplimit_info)))
        dec['DecCopLimit'] = dec_coplimit_info_list

        # 获取使用人信息
        dec_user_fields = ['UseOrgPersonCode', 'UseOrgPersonTel']
        dec_user_infos = _Sql.select('DecUser', *dec_user_fields, where={'DecId': dec_id, 'DeleteFlag': 0})
        dec_user_info_list = []
        for dec_user_info in dec_user_infos:
            dec_user_info_list.append(dict(zip(dec_user_fields, dec_user_info)))
        dec['DecUser'] = dec_user_info_list

        # 获取企业承诺信息
        dec_promise_fields = ['DeclaratioMaterialCode']
        dec_promise_infos = _Sql.select('DecHead', *dec_promise_fields, where={'DecId': dec_id})
        dec_promise_info_list = []
        for dec_promise_info in dec_promise_infos:
            dec_promise_info_list.append(dict(zip(dec_promise_fields, dec_promise_info)))
        dec['DecCopPromise'] = dec_promise_info_list

        # 获取其他包装信息
        dec_otherpack_fields = ['PackQty', 'PackType']
        dec_otherpack_infos = _Sql.select('DecOtherPack', *dec_otherpack_fields, where={'DecId': dec_id, 'DeleteFlag': 0})
        dec_otherpack_info_list = []
        for dec_otherpack_info in dec_otherpack_infos:
            dec_otherpack_info_list.append(dict(zip(dec_otherpack_fields, dec_otherpack_info)))
        dec['DecOtherPack'] = dec_otherpack_info_list

        # 获取随附单据信息
        dec_docrealation_fields = ['EdocID', 'EdocCode', 'EdocFomatType', 'OpNote', 'EdocCopId',
                                   'EdocOwnerCode', 'SignUnit', 'SignTime', 'EdocOwnerName', 'EdocSize']
        dec_docrealation_infos = _Sql.select('LicenseDoc', *dec_docrealation_fields,
                                             where={'clientseqno': ClientSeqNo, 'DeleteFlag': 0})
        dec_docrealation_info_list = []
        for dec_docrealation_info in dec_docrealation_infos:
            dec_docrealation_info_list.append(dict(zip(dec_docrealation_fields, dec_docrealation_info)))
        dec['EdocRealations'] = dec_docrealation_info_list

        logger.info(dec)
        dec['DecSign'] = {'ClientSeqNo': ClientSeqNo}

        if dec['EdocRealations']:
            xml_file_name = os.path.join(settings.LICENSE_XML_DIR, "Dec" + ClientSeqNo + ".xml")
        else:
            xml_file_name = os.path.join(settings.XML_DIR, "Dec" + ClientSeqNo + ".xml")

        # _xml = xml.Xml(xml_file_name,dec) #将dec传入xml然后保存到磁盘先
        _xml = only_win.Xml(xml_file_name, dec)  # 将dec传入xml然后保存到磁盘先,单一窗口类型
        _xml.save()
        logger.info('生成报关单xml报文，自编号{}'.format(ClientSeqNo))
        if settings.DEBUG:
            d = {
                "DecState": 'TS_REQ',
            }
            # 更新状态为“草单，申报提交”
            _Sql.update("DecMsg", where={"ClientSeqNo": ClientSeqNo, 'DeleteFlag': 0}, **d)
            logger.info('更新DecMsg状态为TS_REQ，自编号{}'.format(ClientSeqNo))

        # 修改报关单状态，防止再次将该单据作为任务提交
    # dec_infos = _Sql.update("DecMsg",  where={"DecId": dec_id}, DecState="TS_REQ")

    def upload_QP_task_special(self, dec_info):
        """
        将报关单提交到QP的任务
        :param dec_info: 报关单信息,是一个元组,内容:("DecId", "ClientSeqNo", "DecState", "CreateUser")
        :return:
        """
        dec_id = dec_info[0]
        ClientSeqNo = dec_info[1]
        MoreCategory = dec_info[4]

        _Sql = sql.Sql()
        dec = {}

        # 获取表头数据
        dec_head_fields = ["DecHeadId", "DecId", "SeqNo", "IEFlag", "AgentCode", "AgentName", "ApprNo",
                           "BillNo", "ContrNo", "CustomMaster", "CutMode", "DistinatePort",
                           "FeeCurr", "FeeMark", "FeeRate", "GrossWet", "IEDate", "IEPort",
                           "InsurCurr", "InsurMark", "InsurRate", "LicenseNo", "ManualNo",
                           "NetWt", "Notes", "OtherCurr", "OtherMark", "OtherRate", "OwnerCode",
                           "OwnerName", "PackNo", "TradeCode", "TradeCountry",
                           "TradeMode", "TradeName", "TrafMode", "TrafName", "TransMode", "WrapType",
                           "EntryId", "PreEntryId", "EdiId", "Risk", "CopName", "CopCode",
                           "EntryType", "PDate", "TypistNo", "InputerName", "PartenerID", "TgdNo",
                           "DataSource", "DeclTrnRel", "ChkSurety", "BillType", "AgentCodeScc", "OwnerCodeScc",
                           "TradeCoScc", "CopCodeScc", "PromiseItmes", "TradeAreaCode", 'MarkNo', 'DespPortCode',
                           'EntyPortCode', 'GoodsPlace', 'OverseasConsignorEname', 'OverseasConsignorCode',
                           'OverseasConsigneeEname', 'OverseasConsigneeCode', 'CorrelationNo', 'SpecDeclFlag',
                           'TradeCiqCode', 'OwnerCiqCode', 'DeclCiqCode', 'OrigBoxFlag', 'CorrelationReasonFlag',
                           'InspOrgCode', 'PurpOrgCode', 'BLNo', 'TaxAaminMark', 'CheckFlow', 'OrgCode', 'VsaOrgCode',
                           'DespDate', 'Type']

        dec_head_info = _Sql.select("SpecialDechead", *dec_head_fields, where={"DecId": dec_id})

        h = dict(zip(dec_head_fields, dec_head_info[0]))

        # 数值型 为0.0000时，赋空值
        for i in h:
            if isinstance(h[i], decimal.Decimal) and not h[i]:
                h[i] = ""

        OtherRate = h.get("OtherRate")
        #
        # OtherRate = float(OtherRate)

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

        # if not h["PayWay"]:
        # h["PayWay"]=1  #测试用
        ieflag = h['IEFlag']
        if 'I' == ieflag:
            if not h['IEDate']:
                h['IEDate'] = datetime.datetime.now().strftime("%Y%m%d")
                # 需要添加到数据库
                _Sql.update("DecHead", where={"DecId": dec_id}, IEDate=h['IEDate'])
        dec['DecHead'] = h

        # 获取表体数据
        dec_list_fields = ["id", "DecId", "GNo", "ClassMark", "CodeTs", "ContrItem",
                           "DeclPrice", "DutyMode", "Factor", "GModel", "GName", "OriginCountry",
                           "TradeCurr", "DeclTotal", "GQty", "FirstQty", "SecondQty", "GUnit",
                           "FirstUnit", "SecondUnit", "UseTo", "WorkUsd", "ExgNo", "ExgVersion",
                           "DestinationCountry", 'DistrictCode', 'CiqCode', 'OrigPlaceCode', 'CiqName', 'GoodsAttr',
                           'GoodsSpec', 'Purpose', 'NoDangFlag', 'UnCode', 'DangName', 'DangPackType', 'DangPackSpec',
                           'DestCode', 'Stuff', 'ProdValidDt', 'ProdQgp', 'EngManEntCnm', 'GoodsModel',
                           'GoodsBrand', 'ProduceDate', 'ProdBatchNo']
        dec_lists_info = _Sql.select("SpecialDeclist", *dec_list_fields, where={"DecId": dec_id, 'DeleteFlag': 0})
        dec_list_list = []
        dec['DecGoodsLimits'] = {}
        dec['DecGoodsLimitVins'] = {}
        for dec_list_info in dec_lists_info:
            d = dict(zip(dec_list_fields, dec_list_info))

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

            # 取许可证信息
            dec_goodslimit_fields = ['DecListId', 'GoodsNo', 'LicTypeCode', 'LicenceNo', 'LicWrtofDetailNo',
                                     'LicWrtofQty']
            dec_goodslimitvin_fields = ['DecListId', 'LicenceNo', 'LicTypeCode', 'VinNo', 'BillLadDate', 'QualityQgp',
                                        'MotorNo', 'VinCode', 'ChassisNo', 'InvoiceNum', 'ProdCnnm', 'ProdEnnm',
                                        'ModelEn', 'PricePerUnit']

            dec_goodslimit_infos = _Sql.select("SpecialDecGoodsLimit", *dec_goodslimit_fields,
                                               where={"DecListId": d['id'], 'DeleteFlag': 0})
            for dec_goodslimit_info in dec_goodslimit_infos:
                goodslimit_dict = dict(zip(dec_goodslimit_fields, dec_goodslimit_info))
                dec['DecGoodsLimits'][d['id']] = goodslimit_dict

            dec_goodslimitvin_infos = _Sql.select("SpecialDecGoodsLimitVin", *dec_goodslimitvin_fields,
                                                  where={"DecListId": d['id'], 'DeleteFlag': 0})
            for dec_goodslimitvin_info in dec_goodslimitvin_infos:
                goodslimitvin_dict = dict(zip(dec_goodslimitvin_fields, dec_goodslimitvin_info))
                dec['DecGoodsLimitVins'][d['id']] = goodslimitvin_dict

        # 出口报关单，OriginCountry 填目的国。此处暂时只修改单独一次申报的
        if 'E' == ieflag and 0 == MoreCategory:
            for dec_list in dec_list_list:
                dec_list['OriginCountry'], dec_list['DestinationCountry'] = dec_list['DestinationCountry'], \
                                                                                    dec_list['OriginCountry']
        dec['DecLists'] = dec_list_list

        # 获取集装箱数据
        dec_container_fields = ["ContainerId", "ContainerMd", "GoodsNo", 'LclFlag', 'ContainerWt']
        dec_containers_info = _Sql.select("SpecialDeccontainer", *dec_container_fields,
                                          where={"DecId": dec_id, 'DeleteFlag': 0})
        dec_container_list = []
        for dec_container_info in dec_containers_info:
            dec_container_list.append(dict(zip(dec_container_fields, dec_container_info)))
        dec['DecContainers'] = dec_container_list

        # 获取单证数据
        dec_license_docu_fields = ["DocuCode", "CertCode"]
        dec_license_docus_info = _Sql.select("SpecialDeclicensedoc", *dec_license_docu_fields,
                                             where={"DecId": dec_id, 'DeleteFlag': 0})
        dec_license_docu_list = []
        for dec_license_docu_info in dec_license_docus_info:
            dec_license_docu_list.append(dict(zip(dec_license_docu_fields, dec_license_docu_info)))
        dec['DecLicenseDocus'] = dec_license_docu_list

        # 获取自由文本信息
        dec_free_txt_fields = ["BonNo", "CusFie", 'RelId', 'RelManNo', 'VoyNo']
        dec_free_txt_infos = _Sql.select("SpecialDecFreeTxt", *dec_free_txt_fields, where={"DecId": dec_id, 'DeleteFlag': 0})
        dec_free_txt_info_list = []
        for dec_free_txt_info in dec_free_txt_infos:
            dec_free_txt_info_list.append(dict(zip(dec_free_txt_fields, dec_free_txt_info)))
        dec['DecFreeTxt'] = dec_free_txt_info_list

        # 获取申请单证信息
        dec_requestcert_fields = ['AppCertCode', 'ApplOri', 'ApplCopyQuan']
        dec_requestcert_infos = _Sql.select('SpecialDecRequestCert', *dec_requestcert_fields,
                                            where={'DecId': dec_id, 'DeleteFlag': 0})
        dec_requestcert_info_list = []
        for dec_requestcert_info in dec_requestcert_infos:
            dec_requestcert_info_list.append(dict(zip(dec_requestcert_fields, dec_requestcert_info)))
        dec['DecRequestCert'] = dec_requestcert_info_list

        # 获取企业资质信息表
        dec_coplimit_fields = ['EntQualifNo', 'EntQualifTypeCode']
        dec_coplimit_infos = _Sql.select('SpecialDecCopLimit', *dec_coplimit_fields, where={'DecId': dec_id, 'DeleteFlag': 0})
        dec_coplimit_info_list = []
        for dec_coplimit_info in dec_coplimit_infos:
            dec_coplimit_info_list.append(dict(zip(dec_coplimit_fields, dec_coplimit_info)))
        dec['DecCopLimit'] = dec_coplimit_info_list

        # 获取使用人信息
        dec_user_fields = ['UseOrgPersonCode', 'UseOrgPersonTel']
        dec_user_infos = _Sql.select('SpecialDecUser', *dec_user_fields, where={'DecId': dec_id, 'DeleteFlag': 0})
        dec_user_info_list = []
        for dec_user_info in dec_user_infos:
            dec_user_info_list.append(dict(zip(dec_user_fields, dec_user_info)))
        dec['DecUser'] = dec_user_info_list

        # 获取企业承诺信息
        dec_promise_fields = ['DeclaratioMaterialCode']
        dec_promise_infos = _Sql.select('SpecialDechead', *dec_promise_fields, where={'DecId': dec_id})
        dec_promise_info_list = []
        for dec_promise_info in dec_promise_infos:
            dec_promise_info_list.append(dict(zip(dec_promise_fields, dec_promise_info)))
        dec['DecCopPromise'] = dec_promise_info_list

        # 获取其他包装信息
        dec_otherpack_fields = ['PackQty', 'PackType']
        dec_otherpack_infos = _Sql.select('SpecialDecOtherPack', *dec_otherpack_fields, where={'DecId': dec_id, 'DeleteFlag': 0})
        dec_otherpack_info_list = []
        for dec_otherpack_info in dec_otherpack_infos:
            dec_otherpack_info_list.append(dict(zip(dec_otherpack_fields, dec_otherpack_info)))
        dec['DecOtherPack'] = dec_otherpack_info_list

        # 获取随附单据信息
        dec_docrealation_fields = ['EdocID', 'EdocCode', 'EdocFomatType', 'OpNote', 'EdocCopId',
                                   'EdocOwnerCode', 'SignUnit', 'SignTime', 'EdocOwnerName', 'EdocSize']
        dec_docrealation_infos = _Sql.select('LicenseDoc', *dec_docrealation_fields,
                                             where={'clientseqno': ClientSeqNo, 'DeleteFlag': 0})
        dec_docrealation_info_list = []
        for dec_docrealation_info in dec_docrealation_infos:
            dec_docrealation_info_list.append(dict(zip(dec_docrealation_fields, dec_docrealation_info)))
        dec['EdocRealations'] = dec_docrealation_info_list

        logger.info(dec)
        dec['DecSign'] = {'ClientSeqNo': ClientSeqNo}

        if dec['EdocRealations']:
            xml_file_name = os.path.join(settings.LICENSE_XML_DIR, "Dec" + ClientSeqNo + ".xml")
        else:
            xml_file_name = os.path.join(settings.XML_DIR, "SpecialDec" + ClientSeqNo + ".xml")

        # _xml = xml.Xml(xml_file_name,dec) #将dec传入xml然后保存到磁盘先
        _xml = only_win.Xml(xml_file_name, dec)  # 将dec传入xml然后保存到磁盘先,单一窗口类型
        _xml.save()
        logger.info('生成报关单xml报文，自编号{}'.format(ClientSeqNo))
        if settings.DEBUG:
            d = {
                "DecState": 'TS_REQ',
            }
            # 更新状态为“草单，申报提交”
            _Sql.update("SpecialDecmsg", where={"ClientSeqNo": ClientSeqNo, 'DeleteFlag': 0}, **d)
            logger.info('更新SpecialDecMsg状态为TS_REQ，自编号{}'.format(ClientSeqNo))

        # 修改报关单状态，防止再次将该单据作为任务提交
