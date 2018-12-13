# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/5.
import os
import re
from xml.etree import ElementTree as ET

import copy

from conf.settings import BASE_DIR


class Xml(object):
    def __init__(self, file_path, dec,):
        """
        :param file_path: 保存文件的路径
        :param dec: 报关单中所有的信息,是一个json格式的对象
        """
        template_path = os.path.join(BASE_DIR, "conf", "OnlyWindowspdf.xml")  # xml模板路径
        self.file_path = file_path
        self.dec = dec
        ET.register_namespace('', "http://www.chinaport.gov.cn/dec")
        ET.register_namespace('xsd', "http://www.w3.org/2001/XMLSchema")
        ET.register_namespace('xsi', "http://www.w3.org/2001/XMLSchema-instance")

        self.tree = ET.parse(template_path)
        self.root = self.tree.getroot()
        self.ns = self.get_ns()  # 获取xml文件的名称空间
        self.DecHead = self.root.find(self.tag("DecHead"))
        self.DecLists = self.root.find(self.tag("DecLists"))
        self.DecList = copy.deepcopy(self.DecLists.find(self.tag("DecList")))  # 一个item
        self.DecContainers = self.root.find(self.tag("DecContainers"))
        self.DecContainer = self.root.find(self.tag("DecContainer"))
        self.DecLicenseDocus = self.root.find(self.tag("DecLicenseDocus"))
        self.DecLicenseDocu = self.root.find(self.tag("DecLicenseDocu"))
        self.DecFreeTxt = self.root.find(self.tag("DecFreeTxt"))
        self.DecSign = self.root.find(self.tag("DecSign"))
        self.EdocRealation = self.root.find(self.tag("EdocRealation"))

    def get_ns(self):
        ret = re.match(r"({.*?})", self.root.tag)
        if ret:
            return ret.group(0)
        return ""

    def tag(self, tag_name):
        return self.ns + tag_name

    def process(self):
        """开始生产xml文件"""
        self.process_dec_head()
        self.process_dec_lists()

    def process_dec_head(self):
        fields = ["SeqNo", "IEFlag", "Type", "AgentCode", "AgentName", "ApprNo", "BillNo",
                  "ContrNo", "CustomMaster", "CutMode", "DistinatePort", "DistrictCode", "FeeCurr",
                  "FeeMark", "FeeRate", "GrossWet", "IEDate", "IEPort", "InRatio",
                  "InsurCurr", "InsurMark", "InsurRate", "LicenseNo", "ManualNo", "NetWt",
                  "NoteS", "OtherCurr", "OtherMark", "OtherRate", "OwnerCode", "OwnerName",
                  "PackNo", "PayWay", "PaymentMark", "TradeCode", "TradeCountry", "TradeMode",
                  "TradeName", "TrafMode", "TrafName", "TransMode", "WrapType", "EntryId",
                  "AgentLinkMan", "AgentLinkMAIL", "AgentLinkPHONE", "OwnerLinkMan", "OwnerLinkMAIL", "OwnerLinkPHONE",
                  "PreEntryId", "EdiId", "Risk", "CopName", "CopCode", "EntryType",
                  "PDate", "TypistNo", "InputerName", "PartenerID", "TgdNo", "DataSource","InputerNameMAIL", "InputerNamePHONE",
                  "DeclTrnRel", "BillType", "AgentCodeScc", "OwnerCodeScc", "TradeCodeScc",
                  "CopCodeScc", "PromiseItmes", "TradeAreaCode"]

        # 数据库Dechead中没有Type        xml中目前该字段是空
        # 数据库Dechead中没有TCheckFlow  xml中目前该字段是空

        # xml中的NetWt        在数据库Dechead中叫 NetWet
        # xml中的PromiseItmes 在数据库Dechead中叫 PromiseItems


        dec_head = self.dec.get("DecHead")
        for field in fields:
            node = self.DecHead.find(self.tag(field))

            node.text = str(dec_head.get(field, ""))

    def process_dec_lists(self):
        # 删除表体中所有的item先
        for DecList in self.DecLists.findall(self.tag('DecList')):
            self.DecLists.remove(DecList)

        for dec_list in self.dec['DecLists']:
            self._process_dec_list(dec_list)

    def _process_dec_list(self, dec_list):
        """处理表体中的一个item"""
        fields = ["ClassMark", "CodeTS", "ContrItem", "DeclPrice", "DutyMode", "Factor", "GModel",
                  "GName", "GNo", "OriginCountry", "TradeCurr", "DeclTotal", "GQty",
                  "FirstQty", "SecondQty", "GUnit", "FirstUnit", "SecondUnit", "UseTo",
                  "WorkUsd", "ExgNo", "ExgVersion", "DestinationCountry"]
        DecList = copy.deepcopy(self.DecList)

        for field in fields:
            node = DecList.find(self.tag(field))
            node.text = str(dec_list.get(field, ""))

        self.DecLists.append(DecList)

    def save(self):
        ############ 保存文件 ############
        self.process()
        self.tree.write(self.file_path, encoding="utf-8", xml_declaration=True, method='xml')


if __name__ == '__main__':
    path = "Dec20181.xml"
    # s = Xml()
