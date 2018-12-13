# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/7.


"""用来生成单一窗口(simple window)类型的xml文件"""
import datetime
import os
import re
from xml.etree import ElementTree as ET

import copy

from conf.settings import BASE_DIR


class Xml(object):
    def __init__(self, file_path, dec,client_seq_no):
        """
        :param file_path: 保存文件的路径
        :param dec: 报关单中所有的信息,是一个json格式的对象
        """
        template_path = os.path.join(BASE_DIR, "conf", "sw_template.xml")  # xml模板路径
        self.file_path = file_path
        self.dec = dec
        self.client_seq_no=client_seq_no
        ET.register_namespace('xsi', "http://www.w3.org/2001/XMLSchema-instance")
        ET.register_namespace("xsi:noNamespaceSchemaLocation", "SWImportMessagexsd.xsd")

        self.tree = ET.parse(template_path)
        self.root = self.tree.getroot()
        # self.ns = self.get_ns()  # 获取xml文件的名称空间

        self.SWImpHead = self.root.find("SWImpHead")
        self.SWImpData = self.root.find("SWImpData")
        self.DecMessage = self.SWImpData.find("DecMessage")
        self.DecHead = self.DecMessage.find("DecHead")
        self.DecLists = self.DecMessage.find("DecLists")
        self.DecList = copy.deepcopy(self.DecLists.find("DecList"))

        self.DecContainers = self.DecMessage.find("DecContainers")
        self.Container = copy.deepcopy(self.DecContainers.find("Container"))

        self.DecLicenseDocus = self.DecMessage.find("DecLicenseDocus")
        self.LicenseDocu = copy.deepcopy(self.DecLicenseDocus.find("LicenseDocu"))

        self.DecFreeTxt = self.DecMessage.find("DecFreeTxt")
        self.DecSign = self.DecMessage.find("DecSign")
        self.EcoRelation = self.DecMessage.find("EcoRelation")

    def process(self):
        """开始生成xml文件"""
        self.process_dec_head()
        self.process_dec_lists()
        self.process_dec_containers()
        self.process_declicensedocus()

        self.process_decSign()
        self.process_SWImpHead()

    def process_dec_head(self):
        fields = ["SeqNo", "PreEntryId", "ManualNo", "CustomMaster", "IEPort", "BillNo", "TrafMode",
                  "TrafName", "PayWay", "TradeCode", "TradeName", "OwnerCode", "OwnerName",
                  "AgentCode", "AgentName", "DistrictCode", "TradeCountry", "PaymentMark", "TradeMode",
                  "DistinatePort", "TransMode", "CutMode", "FeeMark", "FeeRate", "FeeCurr",
                  "LicenseNo", "InsurMark", "InsurRate", "InsurCurr", "OtherMark", "OtherRate",
                  "OtherCurr", "WrapType", "PackNo", "GrossWet", "NetWt", "NoteS",
                  "ApprNo", "ContrNo", "InRatio", "EntryType", "IEDate", "IEFlag",
                  "AgentLinkMan", "AgentLinkMAIL", "AgentLinkPHONE", "OwnerLinkMan", "OwnerLinkMAIL", "OwnerLinkPHONE",
                  "Type", "EntryId", "EdiId", "Risk", "CopName", "CopCode",
                  "PDate", "TypistNo", "InputerName", "InputerNameMAIL", "InputerNamePHONE", "PartenerID",
                  "TgdNo", "DataSource", "DeclTrnRel", "BillType", "AgentCodeScc", "OwnerCodeScc",
                  "TradeCodeScc", "CopCodeScc", "PromiseItmes", "TradeAreaCode"]

        # 数据库Dechead中没有Type        xml中目前该字段是空
        # 以下字段在数据库中不存在
        # "AgentLinkMan", "AgentLinkMAIL", "AgentLinkPHONE", "OwnerLinkMan", "OwnerLinkMAIL", "OwnerLinkPHONE",
        # "InputerNameMAIL", "InputerNamePHONE",

        # xml中的NetWt        在数据库Dechead中叫 NetWet
        # xml中的PromiseItmes 在数据库Dechead中叫 PromiseItems


        dec_head = self.dec.get("DecHead")
        for field in fields:
            node = self.DecHead.find(field)
            if field == "NetWt":
                name = "NetWet"
            elif field == "PromiseItmes":
                name = "PromiseItems"
            else:
                name = field

            node.text = str(dec_head.get(name, ""))

    def process_dec_lists(self):
        # 删除表体中所有的item先
        for DecList in self.DecLists.findall('DecList'):
            self.DecLists.remove(DecList)

        for dec_list in self.dec['DecLists']:
            self._process_dec_list(dec_list)

    def _process_dec_list(self, dec_list):
        """处理表体中的一个item"""
        fields = ["ClassMark", "CodeTS", "ContrItem", "DeclPrice", "DutyMode", "Factor", "GModel",
                  "GName", "GNo", "OriginCountry", "TradeCurr", "DeclTotal", "GQty",
                  "FirstQty", "SecondQty", "GUnit", "FirstUnit", "SecondUnit", "UseTo",
                  "WorkUsd", "ExgNo", "ExgVersion", "DestinationCountry",
                  ]
        DecList = copy.deepcopy(self.DecList)

        for field in fields:
            node = DecList.find(field)
            if field=="CodeTS":
                val = str(dec_list.get("CodeTs", ""))
            else:
                val = str(dec_list.get(field, ""))
            node.text = val

        self.DecLists.append(DecList)


    def process_dec_containers(self):
        # 删除报关单中所有的containers先
        for Container in self.DecContainers.findall('Container'):
            self.DecContainers.remove(Container)

        for dec_container in self.dec['DecContainers']:
            self._process_dec_container(dec_container)

    def _process_dec_container(self,dec_container):
        """处理集装箱中的一个item"""
        fields = ["ContainerId","ContainerMd","ContainerWt"]
        Container = copy.deepcopy(self.Container)

        for field in fields:
            node = Container.find(field)
            node.text = str(dec_container.get(field, ""))

        self.DecContainers.append(Container)


    def process_declicensedocus(self):
        # 删除报关单中所有的licensedocus先
        for LicenseDocu in self.DecLicenseDocus.findall('LicenseDocu'):
            self.DecLicenseDocus.remove(LicenseDocu)

        for dec_licensedocu in self.dec['DecLicenseDocus']:
            self._process_declicensedocus(dec_licensedocu)


    def _process_declicensedocus(self,dec_licensedocu):
        """处理集单证信息中的一个item"""
        fields = ["DocuCode", "CertCode"]
        LicenseDocu = copy.deepcopy(self.LicenseDocu)

        for field in fields:
            node = LicenseDocu.find(field)
            node.text = str(dec_licensedocu.get(field, ""))

        self.DecLicenseDocus.append(LicenseDocu)

    def process_decSign(self):
        node_sign_date = self.DecSign.find("SignDate")
        date = datetime.datetime.now()
        node_sign_date.text = date.strftime('%Y%m%d%H%M%S') + str(date).split(".")[1][:2]

        node_ClientSeqNo = self.DecSign.find("ClientSeqNo")
        node_ClientSeqNo.text=self.client_seq_no

    def process_SWImpHead(self):
        node_CopMsgId = self.SWImpHead.find("CopMsgId")
        node_CopMsgId.text = "Dec" + self.client_seq_no + ".xml"
        #IEFlag = self.dec.get("DecHead").get("IEFlag")

        #if IEFlag == "E":
            #print(self.client_seq_no,"chu kou")
            #node_CopMsgId.text =  "DecE" + self.client_seq_no + ".xml"
        #elif IEFlag == "I":
            #print(self.client_seq_no, "jin kou")
            #node_CopMsgId.text = "DecI" + self.client_seq_no + ".xml"


    def save(self):
        ############ 保存文件 ############
        self.process()
        self.tree.write(self.file_path, encoding="utf-8", xml_declaration=True, method='xml')


if __name__ == '__main__':
    path = "Dec20181.xml"
    # s = Xml()
    # print(s.gexx())
