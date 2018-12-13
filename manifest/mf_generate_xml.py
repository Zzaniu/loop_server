#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Software    : loop_server
# @File        : mf_generate_xml.py
# @Author      : zaniu (Zzaniu@126.com)
# @Date        : 2018/12/12 20:05
# @Description :
import datetime
import os
import re
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
import copy

from conf.settings import BASE_DIR


class Xml(object):
    def __init__(self, file_path, mf_info, ):
        """
        :param file_path: 保存文件的路径
        :param dec: 报关单中所有的信息,是一个json格式的对象
        """
        if mf_info.get('ClientSeqNo').startswith('K'):
            template_path = os.path.join(BASE_DIR, "manifest", "MT1401.xml")  # 原始舱单xml模板路径
            self.message_type = 'MT1401'
        elif mf_info.get('ClientSeqNo').startswith('L'):
            template_path = os.path.join(BASE_DIR, "manifest", "MT2401.xml")  # 预配舱单xml模板路径
            self.message_type = 'MT2401'
        else:
            raise Exception('自编号有误，自编号:{0!r}'.format(mf_info.get('ClientSeqNo')))

        self.file_path = file_path
        self.mf_info = mf_info
        ET.register_namespace('', "urn:Declaration:datamodel:standard:CN:MT1401:1")
        self.tree = ET.parse(template_path)
        self.root = self.tree.getroot()
        self.root.set('xmlns:xsi', "http://www.w3.org/2001/XMLSchema-instance")
        self.root.set('xmlns:xsd', "http://www.w3.org/2001/XMLSchema")
        # ET.register_namespace('xsi', "http://www.w3.org/2001/XMLSchema-instance")
        # ET.register_namespace('xsd', "http://www.w3.org/2001/XMLSchema")
        self.ns = self.get_ns()  # 获取xml文件的名称空间
        self.message_head = self.root.find(self.tags("Head"))
        self.mf_head = self.root.find(self.tags("Declaration"))
        self.mf_bill = self.root.find(self.tags("Declaration/Consignment"))

    def get_ns(self):
        ret = re.match(r"({.*?})", self.root.tag)
        if ret:
            return ret.group(0)
        return ""

    def tags(self, tag_name):
        """支持带命名空间的多级节点"""
        tag_name = tag_name.split('/')
        list_tagname = []
        for i in tag_name:
            if i.strip():
                list_tagname.append(self.ns + i)

        return '/'.join(list_tagname)

    def process(self):
        """开始生产xml文件"""
        self.process_message_head()
        # self.process_mf_head()
        # self.process_mf_bills()

    def process_message_head(self):
        """报文表头"""
        self.message_head.find(self.tags("MessageID")).text = "CN_{}_1p0_5317796611420_".format(
            self.message_type) + datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]
        self.message_head.find(self.tags("SendTime")).text = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]

    @staticmethod
    def is_not_empty_tag(tag):
        """判断是不是空节点"""
        speace_flag = False
        children_node = tag.getchildren()
        for node in children_node:
            if node.text != '':
                speace_flag = True

        return speace_flag

    def process_mf_head(self):
        """舱单表头"""
        fields_dict = {
            "DeclarationOfficeID": 'DeclarationOfficeID',
            "ID": "DeclarationID",
            "AdditionalInformation/Content": "Content",
            "Agent/ID": "AgentID",
            "BorderTransportMeans/TypeCode": "TypeCode",
            "Carrier/ID": "CarrierID",
            "LoadingLocation/LoadingDateTime": "LoadingDateTime",
            "RepresentativePerson/Name": "RepresentativePersonName",
            "UnloadingLocation/ArrivalDateTime": "ArrivalDateTime",
            "UnloadingLocation/ID": "UnloadingLocationID",
        }
        mf_head = self.mf_info.get("mf_head")
        for field in fields_dict:
            node = self.mf_head.find(self.tags(field))
            node.text = str(mf_head.get(fields_dict.get(field)))
            if 'None' == node.text:
                node.text = ''

    def process_mf_bills(self):
        """提运单"""
        # 删除bill先
        self.mf_head.remove(self.mf_head.find(self.tags("Consignment")))
        for mf_bill_info in self.mf_info['ManifestBill']:
            self._process_mf_bill(mf_bill_info)

    def _process_mf_bill(self, mf_bill_info):
        """处理表体中的一个item"""
        fields_dict = {
            "GrossVolumeMeasure": "GrossVolumeMeasure",
            "TotalPackageQuantity": "TotalPackageQuantity",
            "ValueAmount": "ValueAmount",
            "TransitDestination/ID": "TransitDestinationID",
            "TransportContractDocument/ID": "TransportContractDocumentID",
            "TransportContractDocument/ConditionCode": "ConditionCode",
            "TransportContractDocument/Deconsolidator/ID": "DeconsolidatorID",
            "Freight/PaymentMethodCode": "PaymentMethodCode",
            "GovernmentAgencyGoodsItem/GoodsMeasure/GrossMassMeasure": "GrossMassMeasure",
            "GovernmentProcedure/CurrentCode": "CurrentCode",
        }
        mf_bill_tag = copy.deepcopy(self.mf_bill)

        for field in fields_dict:
            node = mf_bill_tag.find(self.tags(field))
            node.text = str(mf_bill_info.get(fields_dict.get(field)))
            if 'None' == node.text:
                node.text = ''
        wayto_tag = mf_bill_tag.find(self.tags('BorderTransportMeans/Itinerary'))
        consignees_tag = mf_bill_tag.find(self.tags('Consignee'))
        commoditeitem_tag = mf_bill_tag.find(self.tags('ConsignmentItem'))
        consigner_tag = mf_bill_tag.find(self.tags('Consignor'))
        notifyparty_tag = mf_bill_tag.find(self.tags('NotifyParty'))
        container_tag = mf_bill_tag.find(self.tags('TransportEquipment'))
        undgcontactr_tag = mf_bill_tag.find(self.tags('UNDGContact'))
        self.process_waytos(wayto_tag, mf_bill_info['id'])
        self.process_consignees(mf_bill_tag, consignees_tag, mf_bill_info['id'])
        self.process_commoditeitems(mf_bill_tag, commoditeitem_tag, mf_bill_info['id'])
        self.process_consigners(mf_bill_tag, consigner_tag, mf_bill_info['id'])
        self.process_notifypartys(mf_bill_tag, notifyparty_tag, mf_bill_info['id'])
        self.process_containers(mf_bill_tag, container_tag, mf_bill_info['id'])
        self.process_undgcontacts(mf_bill_tag, undgcontactr_tag, mf_bill_info['id'])
        if self.is_not_empty_tag(mf_bill_tag):
            self.mf_head.append(mf_bill_tag)

    def process_waytos(self, wayto_tag, bill_id):
        """途经国家"""
        _wayto_tag = wayto_tag.find(self.tags('RoutingCountryCode'))
        wayto_tag.remove(_wayto_tag)
        wayto_infos = self.mf_info['WayToCountries'].get(bill_id)
        for _info in wayto_infos:
            _wayto_tag.text = _info.get('RoutingCountryCode')
            if self.is_not_empty_tag(_wayto_tag):
                wayto_tag.append(_wayto_tag)

    def process_consignees(self, mf_bill_tag, consignees_tag, bill_id):
        """收货人信息"""
        mf_bill_tag.remove(consignees_tag)
        consignees_infos = self.mf_info['Consignee'].get('bill_id')
        for consignees_info in consignees_infos:
            self.process_consignee(mf_bill_tag, consignees_tag, consignees_info)

    def process_consignee(self, mf_bill_tag, consignees_tag, consignees_info):
        """收货人信息"""
        fields_dict = {
            "ID": 'ConsigneeID',
            "Name": 'ConsigneeName',
            "Communication/ID": 'CommunicationID',
            "Communication/TypeID": 'CommunicationTypeID'
        }
        for field in fields_dict:
            node = consignees_tag.find(self.tags(field))
            node.text = str(consignees_info.get(fields_dict.get(field)))
            if 'None' == node.text:
                node.text = ''
        contact_tag = consignees_tag.find(self.tags('Contact'))
        self.process_contacts(consignees_tag, contact_tag, consignees_info.get('id'))
        if self.is_not_empty_tag(consignees_tag):
            mf_bill_tag.append(consignees_tag)

    def process_contacts(self, consignees_tag, contact_tag, consignee_id):
        """收货人详情"""
        consignees_tag.remove(contact_tag)
        consignees_infos = self.mf_info['ContactConsignee'].get(consignee_id)
        for consignees_info in consignees_infos:
            self.process_contact(consignees_tag, contact_tag, consignees_info)

    def process_contact(self, consignees_tag, contact_tag, consignees_info):
        """收货人详情"""
        fields_dict = {
            "Name": 'ContactName',
            "Communication/ID": 'CommunicationID',
            "Communication/TypeID": 'CommunicationTypeID',
        }
        for field in fields_dict:
            node = contact_tag.find(self.tags(field))
            node.text = str(consignees_info.get(fields_dict.get(field)))
            if 'None' == node.text:
                node.text = ''
        if self.is_not_empty_tag(contact_tag):
            consignees_tag.append(contact_tag)

    def process_commoditeitems(self, mf_bill_tag, commoditeitem_tag, bill_id):
        """商品信息"""
        mf_bill_tag.remove(commoditeitem_tag)
        commoditeitem_infos = self.mf_info['CommoditeItem'].get(bill_id)
        for info in commoditeitem_infos:
            self.process_commoditeitem(mf_bill_tag, commoditeitem_tag, info)

    def process_commoditeitem(self, mf_bill_tag, commoditeitem_tag, commoditeitem_info):
        """商品信息"""
        fields_dict = {
            "SequenceNumeric": 'SequenceNumeric',
            "Commodity/CargoDescription": 'CargoDescription',
            "Commodity/Description": 'Description',
            "Commodity/Classification/ID": 'ClassificationID',
            "GoodsMeasure/GrossMassMeasure": 'GrossMassMeasure',
            "Packaging/QuantityQuantity": 'QuantityQuantity',
        }
        for field in fields_dict:
            node = commoditeitem_tag.find(self.tags(field))
            node.text = str(commoditeitem_info.get(fields_dict.get(field)))
            if 'None' == node.text:
                node.text = ''
        if self.is_not_empty_tag(commoditeitem_tag):
            mf_bill_tag.append(commoditeitem_tag)

    def process_consigners(self, mf_bill_tag, consigner_tag, bill_id):
        """发货人信息"""
        mf_bill_tag.remove(consigner_tag)
        consigner_infos = self.mf_info['Consigner'].get(bill_id)
        for info in consigner_infos:
            self.process_consigner(mf_bill_tag, consigner_tag, info)

    def process_consigner(self, mf_bill_tag, consigner_tag, consigner_info):
        """发货人信息"""
        fields_dict = {
            "ID": 'ConsignorID',
            "Name": 'ConsignorName',
            "Communication/ID": 'CommunicationID',
            "Communication/TypeID": 'CommunicationTypeID',
        }
        for field in fields_dict:
            node = consigner_tag.find(self.tags(field))
            node.text = str(consigner_info.get(fields_dict.get(field)))
            if 'None' == node.text:
                node.text = ''
        if self.is_not_empty_tag(consigner_tag):
            mf_bill_tag.append(consigner_tag)

    def process_notifypartys(self, mf_bill_tag, notifyparty_tag, bill_id):
        """通知人信息"""
        mf_bill_tag.remove(notifyparty_tag)
        notifyparty_infos = self.mf_info['NotifyParty'].get(bill_id)
        for info in notifyparty_infos:
            self.process_notifyparty(mf_bill_tag, notifyparty_tag, info)

    def process_notifyparty(self, mf_bill_tag, notifyparty_tag, notifyparty_info):
        """通知人信息"""
        fields_dict = {
            "ID": 'ConsignorID',
            "Name": 'ConsignorName',
            "Communication/ID": 'CommunicationID',
            "Communication/TypeID": 'CommunicationTypeID',
        }
        for field in fields_dict:
            node = notifyparty_tag.find(self.tags(field))
            node.text = str(notifyparty_info.get(fields_dict.get(field)))
            if 'None' == node.text:
                node.text = ''
        if self.is_not_empty_tag(notifyparty_tag):
            mf_bill_tag.append(notifyparty_tag)

    def process_containers(self, mf_bill_tag, container_tag, bill_id):
        """集装箱信息"""
        mf_bill_tag.remove(container_tag)
        container_infos = self.mf_info['Container'].get(bill_id)
        for info in container_infos:
            self.process_container(mf_bill_tag, container_tag, info)

    def process_container(self, mf_bill_tag, container_tag, consigner_info):
        """集装箱信息"""
        fields_dict = {
            "ID": 'TransportEquipmentID',
        }
        for field in fields_dict:
            node = container_tag.find(self.tags(field))
            node.text = str(consigner_info.get(fields_dict.get(field)))
            if 'None' == node.text:
                node.text = ''
        if self.is_not_empty_tag(container_tag):
            mf_bill_tag.append(container_tag)

    def process_undgcontacts(self, mf_bill_tag, undgcontactr_tag, bill_id):
        """危险品信息"""
        mf_bill_tag.remove(undgcontactr_tag)
        undgcontactr_infos = self.mf_info['NotifyParty'].get(bill_id)
        for info in undgcontactr_infos:
            self.process_undgcontact(mf_bill_tag, undgcontactr_tag, info)

    def process_undgcontact(self, mf_bill_tag, undgcontactr_tag, undgcontactr_info):
        """危险品信息"""
        fields_dict = {
            "Name": 'UNDGContactName',
            "Communication/ID": 'UNDGContactID',
            "Communication/TypeID": 'UNDGContactTypeID',
        }
        for field in fields_dict:
            node = undgcontactr_tag.find(self.tags(field))
            node.text = str(undgcontactr_info.get(fields_dict.get(field)))
            if 'None' == node.text:
                node.text = ''
        if self.is_not_empty_tag(undgcontactr_tag):
            mf_bill_tag.append(undgcontactr_tag)

    def save(self):
        ############ 保存文件 ############
        self.process()
        self.tree.write(self.file_path, encoding="utf-8", xml_declaration=True, method='xml')


if __name__ == '__main__':
    path = r"C:\ImpPath\RMft\GenerateXml"
    xml_file_name = os.path.join(path, "Manifest111.xml")
    mf = {
        'ClientSeqNo': 'K0153456435'
    }
    _xml = Xml(xml_file_name, mf)  # 将dec传入xml然后保存到磁盘先,单一窗口类型
    _xml.save()
