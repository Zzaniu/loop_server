#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Software    : loop_server
# @File        : mf_process.py
# @Author      : zaniu (Zzaniu@126.com)
# @Date        : 2018/12/12 20:05
# @Description :
import os
import time
import decimal

import datetime
import traceback
from multiprocessing import Process
from threading import Thread

from conf import settings
from manifest.mf_generate_xml import Xml
from utils import log, mail, sql

logger = log.getlogger(__name__)


class MFProcess(Process):
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
                time.sleep(settings.LOOP_TIME)
            except Exception as e:
                logger.exception(e)
                mail.send_email(text=str(traceback.format_exc()), subject="db线程异常,请火速前往处理")
                logger.warn("db线程异常,以邮件通知")
                time.sleep(settings.EXCEPTION_WAIT_TIME)

    def exec_task(self):
        _Sql = sql.Sql()
        mf_infos = _Sql.select("ManifestMsg", "id", "ClientSeqNo", "DecState", "CreateUser", 'MoreCategory',
                                where={"DecState": 'TS_RDY', "DeleteFlag": "0"})
        logger.info(mf_infos)
        # 先全部取出来
        needed_process_mfs = [mf_info for mf_info in mf_infos]
        threads = []
        for mf_info in needed_process_mfs:
            t = Thread(target=self.upload_QP_task, args=(mf_info,))
            threads.append(t)
        for i in threads:
            i.start()
        for i in threads:
            i.join()

    def upload_QP_task(self, mf_info):
        """
        将报关单提交到QP的任务
        :param dec_info: 报关单信息,是一个元组,内容:("mfid", "ClientSeqNo", "DecState", "CreateUser")
        :return: 
        """
        mf_id = mf_info[0]
        ClientSeqNo = mf_info[1]

        _Sql = sql.Sql()
        mf = {}

        # 获取表头数据
        mf_head_fields = ["id", "ManifestMsg", "DeclarationOfficeID", "DeclarationID", "Content", "AgentID", "TypeCode",
                          "CarrierID", "LoadingDateTime", "RepresentativePersonName", "ArrivalDateTime",
                          "UnloadingLocationID"]

        mf_head_info = _Sql.select("ManifestHead", *mf_head_fields, where={"ManifestMsg": mf_id})

        mf['ManifestHead'] = dict(zip(mf_head_fields, mf_head_info[0]))

        # 获取表体数据
        mf_bill_fields = ["id", "ManifestMsg", "GrossVolumeMeasure", "TotalPackageQuantity", "ValueAmount",
                          "TransitDestinationID", "TransportContractDocumentID", "ConditionCode", "DeconsolidatorID",
                          "PaymentMethodCode", "GrossMassMeasure", "CurrentCode"]
        mf_bills_info = _Sql.select("ManifestBill", *mf_bill_fields, where={"ManifestMsg": mf_id, 'DeleteFlag': 0})
        mf_bill_list = []
        # 途经国家
        mf_wayto_fields = ['id', 'ManifestBill', 'RoutingCountryCode']
        # 收货人信息
        mf_consignee_fields = ['id', 'ManifestBill', 'ConsigneeID', 'ConsigneeName', 'CommunicationID',
                               'CommunicationTypeID']
        # 收货具体联系人信息
        mf_cconsignee_fields = ['id', 'ManifestConsignee', 'ContactName', 'CommunicationID', 'CommunicationTypeID']
        # 商品信息
        mf_commoditeitem_fields = ['id', 'ManifestBill', 'SequenceNumeric', 'CargoDescription', 'Description',
                                   'ClassificationID', 'GrossMassMeasure', 'QuantityQuantity']
        # 发货人信息
        mf_consigner_fields = ['id', 'ManifestBill', 'ConsignorID', 'ConsignorName', 'CommunicationID',
                               'CommunicationTypeID']
        # 通知人信息
        mf_notifyparty_fields = ['id', 'ManifestBill', 'NotifyPartyID', 'NotifyPartyName',
                                 'NotifyPartyAddresslIine', 'CommunicationID', 'CommunicationTypeID']
        # 集装箱信息
        mf_container_fields = ['id', 'ManifestBill', 'TransportEquipmentID', ]
        # 危险品信息
        mf_undgcontact_fields = ['id', 'ManifestBill', 'UNDGContactName', 'UNDGContactID', 'UNDGContactTypeID']
        for mf_bill_info in mf_bills_info:
            d = dict(zip(mf_bill_fields, mf_bill_info))
            for i in d:
                if isinstance(d[i], decimal.Decimal) and not d[i]:
                    d[i] = ""
            mf_bill_list.append(d)
            mf['WayToCountries'].update(self.collect_info(_Sql, mf_wayto_fields, 'WayToCountries', 'ManifestBill', d['id']))
            mf['CommoditeItem'].update(self.collect_info(_Sql, mf_commoditeitem_fields, 'CommoditeItem', 'ManifestBill', d['id']))
            mf['Consigner'].update(self.collect_info(_Sql, mf_consigner_fields, 'Consigner', 'ManifestBill', d['id']))
            mf['NotifyParty'].update(self.collect_info(_Sql, mf_notifyparty_fields, 'NotifyParty', 'ManifestBill', d['id']))
            mf['Container'].update(self.collect_info(_Sql, mf_container_fields, 'Container', 'ManifestBill', d['id']))
            mf['UNDGContact'].update(self.collect_info(_Sql, mf_undgcontact_fields, 'UNDGContact', 'ManifestBill', d['id']))
            mf['Consignee'].update(self.collect_info(_Sql, mf_consignee_fields, 'Consignee', 'ManifestBill', d['id']))

        mf['ManifestBill'] = mf_bill_list
        for _dict in mf['Consignee']:
            mf['ContactConsignee'].update(self.collect_info(_Sql, mf_cconsignee_fields, 'ContactConsignee', 'ManifestConsignee', mf['Consignee'][_dict].get('id')))
        mf['ClientSeqNo'] = ClientSeqNo
        print('mf = ', mf)
        xml_file_name = os.path.join(settings.MF_DATA_XML_DIR, "Manifest" + ClientSeqNo + ".xml")

        _xml = Xml(xml_file_name, mf)  # 将dec传入xml然后保存到磁盘先,单一窗口类型
        _xml.save()
        logger.info('生成报关单xml报文，自编号{}'.format(ClientSeqNo))
        if settings.DEBUG:
            d = {
                "DecState": 'TS_REQ',
            }
            _Sql.update("ManifestMsg", where={"ClientSeqNo": ClientSeqNo, 'DeleteFlag': 0}, **d)
            logger.info('更新ManifestMsg状态为TS_REQ，自编号{}'.format(ClientSeqNo))

    def collect_info(self, _sql, fields, tb_name, fk_name, fk_id):
        """
        收集信息
        :param _sql: sql实例
        :param fields: field列表
        :param tb_name: 数据库表名
        :param fk_name: 外键名
        :param fk_id: foreignKey id
        :return: dict
        """
        info = {}
        _infos = _sql.select(tb_name, *fields, where={fk_name: fk_id, 'DeleteFlag': 0})
        for _info in _infos:
            wayto_dict = dict(zip(fields, _info))
            info[fk_id].append(wayto_dict)
        return info
