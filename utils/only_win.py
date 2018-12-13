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
        # template_path = os.path.join(BASE_DIR, "conf", "OnlyWindows.xml")  # xml模板路径
        template_path = os.path.join(BASE_DIR, "conf", "OnlyWindowsNews_1.xml")  # xml模板路径
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
        self.DecGoodsLimits = self.DecList.find(self.tag('DecGoodsLimits'))
        self.DecGoodsLimit = self.DecGoodsLimits.find(self.tag('DecGoodsLimit'))
        # self.DecGoodsLimitVin = self.DecGoodsLimit.find(self.tag('DecGoodsLimitVin'))
        self.DecContainers = self.root.find(self.tag("DecContainers"))
        self.Container = self.root.find(self.mytag("DecContainers/Container"))
        self.DecContainer = self.root.find(self.tag("DecContainer"))
        self.DecLicenseDocus = self.root.find(self.tag("DecLicenseDocus"))
        self.DecLicenseDocu = self.root.find(self.mytag("DecLicenseDocus/LicenseDocu"))
        self.DecFreeTxt = self.root.find(self.tag("DecFreeTxt"))
        self.DecSign = self.root.find(self.tag("DecSign"))
        self.EdocRealation = self.root.find(self.tag("EdocRealation"))
        self.DecFreeTxt = self.root.find(self.tag('DecFreeTxt'))
        self.DecCopLimits = self.root.find(self.tag('DecCopLimits'))
        self.DecCopLimit = self.DecCopLimits.find(self.tag('DecCopLimit'))
        self.DecRequestCerts = self.root.find(self.tag('DecRequestCerts'))
        self.DecRequestCert = self.DecRequestCerts.find(self.tag('DecRequestCert'))
        self.DecOtherPacks = self.root.find(self.tag('DecOtherPacks'))
        self.DecOtherPack = self.DecOtherPacks.find(self.tag('DecOtherPack'))
        self.DecUsers = self.root.find(self.tag('DecUsers'))
        self.DecUser = self.DecUsers.find(self.tag('DecUser'))
        self.DecCopPromises = self.root.find(self.tag('DecCopPromises'))
        self.DecCopPromise = self.DecCopPromises.find(self.tag('DecCopPromise'))

    def get_ns(self):
        ret = re.match(r"({.*?})", self.root.tag)
        if ret:
            return ret.group(0)
        return ""

    def mytag(self, tag_name):
        tag_name = tag_name.split('/')
        list_tagname = []
        for i in tag_name:
            list_tagname.append(self.ns + i)

        return '/'.join(list_tagname)

    def tag(self, tag_name):
        return self.ns + tag_name

    def process(self):
        """开始生产xml文件"""
        self.process_dec_head()
        self.process_dec_lists()
        self.process_dec_decsign()
        self.process_dec_decfreetxt()
        self.process_dec_containers()
        self.process_declicensedocus()
        self.process_dec_requestcerts()
        self.process_dec_coplimits()
        self.process_dec_otherpacks()
        self.process_dec_promises()
        self.process_dec_users()
        self.process_dec_docrealation()

    def process_dec_docrealation(self):
        """随附单据信息"""
        self.root.remove(self.EdocRealation)
        for EdocRealation in self.dec['EdocRealations']:
            self._process_dec_docrealation_item(EdocRealation)

    def _process_dec_docrealation_item(self, EdocRealation):
        """单个item信息"""

        fields = ['EdocID', 'EdocCode', 'EdocFomatType', 'OpNote', 'EdocCopId','EdocOwnerCode', 'SignUnit',
                  'SignTime', 'EdocOwnerName', 'EdocSize']
        _children_tag = copy.deepcopy(self.EdocRealation)
        for field in fields:
            node = _children_tag.find(self.tag(field))
            node.text = str(EdocRealation.get(field))
            if 'None' == node.text:
                node.text = ''

        if self.is_not_empty_tag(_children_tag):
            self.root.append(_children_tag)

    def process_dec_users(self):
        """使用人信息"""
        self.DecUsers.remove(self.DecUser)
        fields = ["UseOrgPersonCode", "UseOrgPersonTel"]
        for dec_user in self.dec['DecUser']:
            self._process_dec_item(fields, dec_user, self.DecUser, self.DecUsers)

    def process_dec_requestcerts(self):
        """申请单证信息"""
        self.DecRequestCerts.remove(self.DecRequestCert)
        fields = ["AppCertCode", "ApplOri", 'ApplCopyQuan']
        for DecRequestCert in self.dec['DecRequestCert']:
            self._process_dec_item(fields, DecRequestCert, self.DecRequestCert, self.DecRequestCerts)

    def process_dec_coplimits(self):
        """企业资质信息"""
        self.DecCopLimits.remove(self.DecCopLimit)
        fields = ['EntQualifNo', 'EntQualifTypeCode']
        for DecCopLimit in self.dec['DecCopLimit']:
            self._process_dec_item(fields, DecCopLimit, self.DecCopLimit, self.DecCopLimits)

    def _process_dec_item(self, fields, dec_info, children_tag, parrent_tags):
        """单个item信息"""
        _children_tag = copy.deepcopy(children_tag)

        for field in fields:
            node = _children_tag.find(self.tag(field))
            node.text = str(dec_info.get(field))
            if 'None' == node.text:
                node.text = ''

        if self.is_not_empty_tag(_children_tag):
            parrent_tags.append(_children_tag)

    def process_dec_otherpacks(self):
        """其他包装信息"""
        self.DecOtherPacks.remove(self.DecOtherPack)
        for dec_otherpack in self.dec['DecOtherPack']:
            self._process_decotherpack(dec_otherpack)

    def _process_decotherpack(self,dec_otherpack):
        """处理其他包装信息中的一个item"""
        fields = ["PackQty", "PackType"]
        DecOtherPack = copy.deepcopy(self.DecOtherPack)

        for field in fields:
            node = DecOtherPack.find(self.tag(field))
            node.text = str(dec_otherpack.get(field))
            if 'None' == node.text:
                node.text = ''

        if self.is_not_empty_tag(DecOtherPack):
            self.DecOtherPacks.append(DecOtherPack)

    def process_dec_promises(self):
        """企业承诺信息"""
        self.DecCopPromises.remove(self.DecCopPromise)
        for dec_coppromise in self.dec['DecCopPromise']:
            fields = ["DeclaratioMaterialCode"]
            DecCopPromise = copy.deepcopy(self.DecCopPromise)

            for field in fields:
                node = DecCopPromise.find(self.tag(field))
                node.text = str(dec_coppromise.get(field))
                if 'None' == node.text:
                    node.text = ''

            if self.is_not_empty_tag(DecCopPromise):
                self.DecCopPromises.append(DecCopPromise)

    def process_declicensedocus(self):
        """集装箱信息"""
        self.DecLicenseDocus.remove(self.DecLicenseDocu)
        for dec_licensedocu in self.dec['DecLicenseDocus']:
            self._process_declicensedocus(dec_licensedocu)

    def _process_declicensedocus(self,dec_licensedocu):
        """处理集单证信息中的一个item"""
        fields = ["DocuCode", "CertCode"]
        LicenseDocu = copy.deepcopy(self.DecLicenseDocu)

        for field in fields:
            node = LicenseDocu.find(self.tag(field))
            node.text = str(dec_licensedocu.get(field))
            if 'None' == node.text:
                node.text = ''

        if self.is_not_empty_tag(LicenseDocu):
            self.DecLicenseDocus.append(LicenseDocu)

    def process_dec_decfreetxt(self):
        """申报地海关为5317深关机场的时候，保税监管场所改为'4403W'"""
        dec_free_txts = self.dec.get("DecFreeTxt")
        fields = ["BonNo", "CusFie", 'RelId', 'RelManNo', 'VoyNo']
        for dec_free_txt in dec_free_txts:
            for field in fields:
                node = self.DecFreeTxt.find(self.tag(field))
                node.text = str(dec_free_txt.get(field))
                if 'None' == node.text:
                    node.text = ''

    def process_dec_decsign(self):
        """DecSign加上ClientSeqNo"""
        fields = ['ClientSeqNo']
        dec_head = self.dec.get("DecSign")
        for field in fields:
            node = self.DecSign.find(self.tag(field))
            name = field

            node.text = str(dec_head.get(name))
            if 'None' == node.text:
                node.text = ''

    def process_dec_containers(self):
        # 删除报关单中所有的containers先
        self.DecContainers.remove(self.Container)
        for dec_container in self.dec['DecContainers']:
            self._process_dec_container(dec_container)

    def _process_dec_container(self, dec_container):
        """处理集装箱中的一个item"""
        fields = ["ContainerId", "ContainerMd", "GoodsNo", 'LclFlag', 'ContainerWt']
        Container = copy.deepcopy(self.Container)

        for field in fields:
            node = Container.find(self.tag(field))
            node.text = str(dec_container.get(field))
            if 'None' == node.text:
                node.text = ''

        if self.is_not_empty_tag(Container):
            self.DecContainers.append(Container)

    @staticmethod
    def is_not_empty_tag(tag):
        """判断是不是空节点"""
        speace_flag = False
        children_node = tag.getchildren()
        for node in children_node:
            if node.text != '':
                speace_flag = True

        return speace_flag

    def process_dec_head(self):
        fields = ["SeqNo", "IEFlag", "Type", "AgentCode", "AgentName", "ApprNo", "BillNo",
                  "ContrNo", "CustomMaster", "CutMode", "DistinatePort", "FeeCurr",
                  "FeeMark", "FeeRate", "GrossWet", "IEDate", "IEPort",
                  "InsurCurr", "InsurMark", "InsurRate", "LicenseNo", "ManualNo", "NetWt",
                  "NoteS", "OtherCurr", "OtherMark", "OtherRate", "OwnerCode", "OwnerName",
                  "PackNo", "TradeCode", "TradeCountry", "TradeMode",
                  "TradeName", "TrafMode", "TrafName", "TransMode", "WrapType", "EntryId",
                  "AgentLinkMan", "AgentLinkMAIL", "AgentLinkPHONE", "OwnerLinkMan", "OwnerLinkMAIL", "OwnerLinkPHONE",
                  "PreEntryId", "EdiId", "Risk", "CopName", "CopCode", "EntryType",
                  "PDate", "TypistNo", "InputerName", "PartenerID", "TgdNo", "DataSource", "DeclTrnRel",
                  "InputerNameMAIL", "InputerNamePHONE", "BillType", "AgentCodeScc", "OwnerCodeScc", "TradeCoScc",
                  "CopCodeScc", "PromiseItmes", "TradeAreaCode", 'MarkNo', 'DespPortCode', 'EntyPortCode', 'GoodsPlace',
                  'OverseasConsignorEname', 'OverseasConsignorCode', 'OverseasConsigneeEname', 'OverseasConsigneeCode',
                  'CorrelationNo', 'SpecDeclFlag', 'TradeCiqCode', 'OwnerCiqCode', 'DeclCiqCode', 'OrigBoxFlag',
                  'CorrelationReasonFlag', 'InspOrgCode', 'PurpOrgCode', 'BLNo', 'TaxAaminMark', 'CheckFlow', 'OrgCode',
                  'VsaOrgCode', 'DespDate',]

        # xml中的NetWt        在数据库Dechead中叫 NetWet
        # xml中的PromiseItmes 在数据库Dechead中叫 PromiseItems


        dec_head = self.dec.get("DecHead")
        for field in fields:
            node = self.DecHead.find(self.tag(field))
            if node is None:
                continue
            elif field == 'NoteS':
                name = 'Notes'
            else:
                name = field

            node.text = str(dec_head.get(name))
            if 'None' == node.text:
                node.text = ''

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
                  "WorkUsd", "ExgNo", "ExgVersion", "DestinationCountry", 'DistrictCode', 'CiqCode', 'OrigPlaceCode',
                  'CiqName', 'GoodsAttr', 'GoodsSpec', 'Purpose', 'NoDangFlag', 'Uncode', 'DangName', 'DangPackType',
                  'DangPackSpec', 'DestCode', 'Stuff', 'ProdValidDt', 'ProdQgp', 'EngManEntCnm', 'GoodsModel',
                  'GoodsBrand', 'ProduceDate', 'ProdBatchNo']
        DecList = copy.deepcopy(self.DecList)

        for field in fields:
            node = DecList.find(self.tag(field))
            if 'CodeTS' == field:
                node.text = str(dec_list.get('CodeTs'))
            elif 'Uncode' == field:
                node.text = str(dec_list.get('UnCode'))
            else:
                node.text = str(dec_list.get(field))
            if 'None' == node.text:
                node.text = ''
            # print("field = %r, node.text = %r" % (field, node.text))
        decgoodslimits_tag = DecList.find(self.tag('DecGoodsLimits'))
        self.process_dec_goodslimits(decgoodslimits_tag, dec_list['id'])
        self.DecLists.append(DecList)

    def process_dec_goodslimits(self, decgoodslimits_tag, dec_list_id):
        decgoodslimits_tag.remove(decgoodslimits_tag.find(self.tag('DecGoodsLimit')))
        goodslimit_dict = self.dec['DecGoodsLimits'].get(dec_list_id)
        if goodslimit_dict:
            self.process_dec_goodslimit(goodslimit_dict, dec_list_id, decgoodslimits_tag)

    def process_dec_goodslimit(self, goodslimit_dict, dec_list_id, decgoodslimits_tag):
        decgoodslimit_tag = copy.deepcopy(self.DecGoodsLimit)
        fields = ['GoodsNo', 'LicTypeCode', 'LicenceNo', 'LicWrtofDetailNo', 'LicWrtofQty']
        for field in fields:
            node = decgoodslimit_tag.find(self.tag(field))
            node.text = str(goodslimit_dict.get(field))
            if 'None' == node.text:
                node.text = ''

        decgoodslimitvin_tag = decgoodslimit_tag.find(self.tag('DecGoodsLimitVin'))
        _decgoodslimitvin_tag = copy.deepcopy(decgoodslimitvin_tag)
        decgoodslimit_tag.remove(decgoodslimitvin_tag)
        goodslimitvin_dict = self.dec['DecGoodsLimitVins'].get(dec_list_id)
        if goodslimitvin_dict:
            self.process_dec_goodslimitvin(goodslimitvin_dict, _decgoodslimitvin_tag, decgoodslimit_tag)
        decgoodslimits_tag.append(decgoodslimit_tag)

    def process_dec_goodslimitvin(self, goodslimitvin_dict, decgoodslimitvin_tag, decgoodslimit_tag):
        fields = ['LicenceNo', 'LicTypeCode', 'VinNo', 'BillLadDate', 'QualityQgp', 'MotorNo',
                  'VinCode', 'ChassisNo', 'InvoiceNum', 'ProdCnnm', 'ProdEnnm', 'ModelEn', 'PricePerUnit']
        for field in fields:
            node = decgoodslimitvin_tag.find(self.tag(field))
            node.text = str(goodslimitvin_dict.get(field))
            if 'None' == node.text:
                node.text = ''

        decgoodslimit_tag.insert(5, decgoodslimitvin_tag)

    def save(self):
        ############ 保存文件 ############
        self.process()
        self.tree.write(self.file_path, encoding="utf-8", xml_declaration=True, method='xml')


if __name__ == '__main__':
    path = "Dec20181.xml"
    # s = Xml()
    # print(s.gexx())
