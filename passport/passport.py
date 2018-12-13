import os
from xml.etree import ElementTree as ET

import copy

from conf.settings import BASE_DIR


class Xml(object):
    def __init__(self, file_path, passport,):
        """
        :param file_path: 保存文件的路径
        :param dec: 报关单中所有的信息,是一个json格式的对象
        """
        # template_path = os.path.join(BASE_DIR, "conf", "TEST20180612MID.xml")  # xml模板路径
        template_path = os.path.join(BASE_DIR, "conf", "PassPort.xml")  # xml模板路径
        self.file_path = file_path
        self.passport = passport

        self.tree = ET.parse(template_path)
        self.root = self.tree.getroot()
        self.PassPortHead = self.root.find('Object/Package/DataInfo/BussinessData/PassPortMessage/PassportHead')
        self.PassportAcmp = self.root.find('Object/Package/DataInfo/BussinessData/PassPortMessage/PassportAcmp')
        self.PassportMessage = self.root.find('Object/Package/DataInfo/BussinessData/PassPortMessage')
        self.DelcareFlag = self.root.find("Object/Package/DataInfo/BussinessData/DelcareFlag")

    def process(self):
        """开始生产xml文件"""
        self.process_passport_head()
        self.process_passport_acmps()

    def process_passport_head(self):
        fields = ["SeqNo", "PassportNo", "PassportTypecd", "MasterCuscd", "DclTypecd",
                  "IoTypecd", "BindTypecd", "RltTbTypecd", "RltNo", "AreainOriactNo", "AreainEtpsno",
                  "AreainEtpsNm", "AreainEtpsSccd", "VehicleNo", "VehicleIcNo", "ContainerNo",
                  "VehicleWt", "VehicleFrameNo", "VehicleFrameWt", "ContainerType", "ContainerWt",
                  "TotalWt", "TotalGrossWt", "TotalNetWt", "DclErConc", "DclEtpsno", "DclEtpsNm",
                  "DclEtpsSccd", "InputCode", "InputSccd", "InputName", "EtpsPreentNo", "Rmk"]

        # 数据库Dechead中没有Type        xml中目前该字段是空
        # 数据库Dechead中没有TCheckFlow  xml中目前该字段是空

        # xml中的NetWt        在数据库Dechead中叫 NetWet
        # xml中的PromiseItmes 在数据库Dechead中叫 PromiseItems
        dec_head = self.passport.get("PassPortHead")
        self.DelcareFlag.text = str(dec_head.get("DelcareFlag", "")).strip()
        for field in fields:
            node = self.PassPortHead.find(field)       # 这里

            name = field
            node.text = str(dec_head.get(name))
            if 'None' == node.text:
                node.text = ''

    def process_passport_acmps(self):
        # 删除表体中所有的item先
        self.PassportMessage.remove(self.PassportAcmp)
        index = 0
        for passport_acmp in self.passport['AcmpList']:
            index += 1
            self._process_passport_acmp(passport_acmp, index)

    def _process_passport_acmp(self, passport_acmp, index):
        """处理表体中的一个item"""
        fields = ["SeqNo", "PassPortNo", "RtlBillTypecd", "RtlBillNo"]
        PassPortAcmp = copy.deepcopy(self.PassportAcmp)
        for field in fields:
            node = PassPortAcmp.find(field)
            if 'RtlBillTypecd' == field:
                name = 'RltTbTypecd'
            elif 'RtlBillNo' == field:
                name = 'RltNo'
            else:
                name = field
            node.text = str(passport_acmp.get(name))
            if 'None' == node.text:
                node.text = ''

        self.PassportMessage.insert(index, PassPortAcmp)

    def save(self):
        """保存文件"""
        self.process()
        tree = self.tree
        tree.write(self.file_path, encoding="utf-8", xml_declaration=True, method='xml')


if __name__ == '__main__':
    path = "Dec20181.xml"
