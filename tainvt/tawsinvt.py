# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/5.
import os
from xml.etree import ElementTree as ET

import copy

from conf.settings import BASE_DIR


class Xml(object):
    def __init__(self, file_path, dec, ):
        """
        :param file_path: 保存文件的路径
        :param dec: 报关单中所有的信息,是一个json格式的对象
        """
        template_path = os.path.join(BASE_DIR, "tainvt", "goldtwo_newsinvt.xml")  # xml模板路径
        self.file_path = file_path
        self.dec = dec

        self.tree = ET.parse(template_path)
        self.root = self.tree.getroot()
        self.DecHead = self.root.find('Object/Package/DataInfo/BussinessData/InvtMessage/InvtHeadType')
        # self.DecList = self.root.find('Object/Package/DataInfo/BussinessData/InvtMessage/InvtListType')
        self.DecLists = self.root.find("Object/Package/DataInfo/BussinessData/InvtMessage")
        self.DecList = self.root.find('Object/Package/DataInfo/BussinessData/InvtMessage/InvtListType')
        self.DelcareFlag = self.root.find("Object/Package/DataInfo/BussinessData/DelcareFlag")
        # self.DecList = copy.deepcopy(self.DecLists.find(self.tag("DecList")))  # 一个item

    # def get_ns(self):
    #     ret = re.match(r"({.*?})", self.root.tag)
    #     if ret:
    #         return ret.group(0)
    #     return ""

    # def tag(self, tag_name):
    #     # return self.ns + tag_name
    #     return tag_name
    def process(self):
        """开始生产xml文件"""
        self.process_dec_head()
        self.process_dec_lists()

    def process_dec_head(self):
        fields = ["SeqNo", "BondInvtNo", "ChgTmsCnt", "PutrecNo", "EtpsInnerInvtNo", "BizopEtpsSccd", "BizopEtpsno",
                  "BizopEtpsNm", "RvsngdEtpsSccd", "RcvgdEtpsno", "RcvgdEtpsNm", "DclEtpsSccd", "DclEtpsno",
                  "DclEtpsNm", "InputCode", "InputCreditCode", "InputName", "InputTime", "InvtDclTime", "EntryDclTime",
                  "EntryNo", "CorrEntryDclEtpsSccd", "CorrEntryDclEtpsNo", "CorrEntryDclEtpsNm", "RltInvtNo",
                  "RltPutrecNo", "RltEntryNo", "RltEntryBizopEtpsSccd", "RltEntryBizopEtpsno", "RltEntryBizopEtpsNm",
                  "RltEntryRvsngdEtpsSccd", "RltEntryRcvgdEtpsno", "RltEntryRcvgdEtpsNm", "RltEntryDclEtpsSccd",
                  "RltEntryDclEtpsNm", "RltEntryDclEtpsno", "ImpexpPortcd", "DclPlcCuscd", "ImpexpMarkcd",
                  "MtpckEndprdMarkcd", "SupvModecd", "TrspModecd", "ApplyNo", "ListType", "DclcusFlag", "DclcusTypecd",
                  "PrevdTime", "FormalVrfdedTime", "InvtIochkptStucd", "VrfdedMarkcd", "IcCardNo", "ListStat",
                  "DecType", "Rmk", "StshipTrsarvNatcd", "InvtType", "EntryStucd", "PassportUsedTypeCd", "AddTime"]

        dec_head = self.dec.get("DecHead")
        self.DelcareFlag.text = str(dec_head.get("DelcareFlag", "")).strip()
        for field in fields:
            node = self.DecHead.find(field)
            if "RltEntryRcvgdEtpsNm" == field:
                name = "RltEntryRcvgdetpsNm"
            elif "RltEntryRcvgdEtpsno" == field:
                name = "RltEntryRcvgdEtpsNo"
            elif "InvtType" == field:
                name = "BondInvtTypecd"
            elif 'CorrEntryDclEtpsNo' == field:
                name = 'CorrEntryDclEtpsno'
            else:
                name = field

            node.text = str(dec_head.get(name.upper(), "")).strip() if dec_head.get(name.upper(), "") else ''
            # print('*****hahaha = ', str(dec_head.get(name, "")))

    def process_dec_lists(self):
        # 删除表体中所有的item先
        # for DecList in self.DecLists.findall(self.DecList):
        #     print("1234567890-")
        #     print("self.DecList.remove(DecList)",self.DecList.remove(DecList))
        #     self.DecList.remove(DecList)
        self.DecLists.remove(self.DecList)
        for dec_list in self.dec['DecLists']:
            self._process_dec_list(dec_list)

    def _process_dec_list(self, dec_list):
        """处理表体中的一个item"""
        fields = ["SeqNo", "GdsSeqno", "PutrecSeqno", "GdsMtno", "Gdecd", "GdsNm", "GdsSpcfModelDesc", "DclUnitcd",
                  "LawfUnitcd", "SecdLawfUnitcd", "Natcd", "DclUprcAmt", "DclTotalAmt", "UsdStatTotalAmt", "DclCurrcd",
                  "LawfQty", "SecdLawfQty", "WtSfVal", "FstSfVal", "SecdSfVal", "DclQty", "GrossWt", "NetWt", "UseCd",
                  "LvyrlfModecd", "UcnsVerno", "EntryGdsSeqno", "ApplyTbSeqno", "ClyMarkcd", "Rmk", "AddTime"]
        DecList = copy.deepcopy(self.DecList)

        for field in fields:
            node = DecList.find(field)
            node.text = str(dec_list.get(field.upper(), "")).strip() if dec_list.get(field.upper(), "") else ''

        self.DecLists.append(DecList)

    # def mytag(self, tag_name):
    #     tag_name = tag_name.split('/')
    #     list_tagname = []
    #     for i in tag_name:
    #         list_tagname.append(self.ns + i)
    #
    #     return '/'.join(list_tagname)

    def save(self):
        ############ 保存文件 ############
        self.process()
        tree = self.tree


        # print('tree = ', tree)


        # print("self.tag('DecHead') = ", self.tag('DecHead/TradeName'))
        # node_list = tree.findall(self.mytag('DecHead/TradeName'))
        # for node in node_list:
        #     print("node.text = ", node.text)
        # print("tree.findall(self.tag('DecHead')) = ", tree.findall(self.tag('DecHead')))

        # self.tree.write(self.file_path, encoding="utf-8", xml_declaration=True, method='xml')
        tree.write(self.file_path, encoding="utf-8", xml_declaration=True, method='xml')


if __name__ == '__main__':
    path = "Dec20181.xml"
    # s = Xml()
    # print(s.gexx())
