# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/5.

import re
from xml.etree import ElementTree as ET


class Xml(object):
    def __init__(self, file_path):
        """
        :param file_path: xml文件的路径
        """
        self.file_path = file_path
        self.str_xml  = open(self.file_path, 'r',encoding="utf-8").read()
        self.root = ET.XML(self.str_xml)
        # self.ns = self.get_ns()  # 获取xml文件的名称空间
        # self.DecHead = self.root.find(self.tag("DecHead"))

    def xxx(self):
        for child in self.root:

        # 第二层节点的标签名称和标签属性
            print(child.tag, child.attrib,"二层节点")
            # 遍历XML文档的第三层
            for i in child:
                # 第二层节点的标签名称和内容
                print(i.tag,i.text)
        tree = ET.ElementTree(self.root)
        tree.write("newnew.xml", encoding='utf-8')



    # def get_ns(self):
    #     ret = re.match(r"({.*?})", self.root.tag)
    #     if ret:
    #         return ret.group(0)
    #     return ""
    #
    # def tag(self, tag_name):
    #     return self.ns + tag_name

    def gexx(self):
        fields = ['SeqNo',
                  'IEFlag',
                  'Type',
                  'AgentCode',
                  'AgentName',
                  'ApprNo',
                  'BillNo',
                  'ContrNo',
                  'CustomMaster',
                  'CutMode',
                  'DistinatePort',
                  'DistrictCode',
                  'FeeCurr',
                  'FeeMark',
                  'FeeRate',
                  'GrossWet',
                  'IEDate',
                  'IEPort',
                  'InRatio',
                  'InsurCurr',
                  'InsurMark',
                  'InsurRate',
                  'LicenseNo',
                  'ManualNo',
                  'NetWt',
                  'NoteS',
                  'OtherCurr',
                  'OtherMark',
                  'OtherRate',
                  'OwnerCode',
                  'OwnerName',
                  'PackNo',
                  'PayWay',
                  'PaymentMark',
                  'TradeCode',
                  'TradeCountry',
                  'TradeMode',
                  'TradeName',
                  'TrafMode',
                  'TrafName',
                  'TransMode',
                  'WrapType',
                  'EntryId',
                  'PreEntryId',
                  'EdiId',
                  'Risk',
                  'CopName',
                  'CopCode',
                  'EntryType',
                  'PDate',
                  'TypistNo',
                  'InputerName',
                  'PartenerID',
                  'TgdNo',
                  'DataSource',
                  'DeclTrnRel',
                  'ChkSurety',
                  'BillType',
                  'AgentCodeScc',
                  'OwnerCodeScc',
                  'TradeCodeScc',
                  'CopCodeScc',
                  'PromiseItmes',
                  'TradeAreaCode',
                  'CheckFlow', ]

        for i in fields:
            node = self.DecHead.find(self.tag(i))
            print(i,node.text)
            if node.text:
                node.text = str(node.text+"1111111")

        ############ 保存文件 ############
        self.tree.write("newnew.xml", encoding='utf-8')



        # # 遍历XML中所有的year节点
        # for node in self.root.iter(self.tag("DecHead")):
        #     # 节点的标签名称和内容
        #     # print(node.tag, node.text)
        #     for i in node:
        #         print(i)


if __name__ == '__main__':
    path = "Dec201802011651490001.xml"
    s = Xml(path)
    print(s.xxx())


    # 直接解析xml文件
    # tree = ET.parse("Dec201802011651490001.xml")
    # tree = ET.parse("Dec2018.xml")
    # tree = ET.parse("xxxx.xml")

    # 获取xml文件的根节点
    # root = tree.getroot()

    # print(root.tag)



    # 遍历XML文档的第二层
    # for child in root:
    #     # 第二层节点的标签名称和标签属性
    #     print(child.tag, child.attrib,"二层节点")
    #     # 遍历XML文档的第三层
    #     for i in child:
    #         # 第二层节点的标签名称和内容
    #         print(i.tag,i.text)

    # 遍历XML中所有的year节点
    # for node in root.iter('DecHead'):
    #     # 节点的标签名称和内容
    #     print(node.tag, node.text)
