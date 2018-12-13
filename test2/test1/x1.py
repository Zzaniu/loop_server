# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/5.

from xml.etree import ElementTree as ET



ET.register_namespace('xsi', "http://www.w3.org/2001/XMLSchema-instance")
ET.register_namespace("xsi:noNamespaceSchemaLocation", "SWImportMessagexsd.xsd")

tree = ET.parse('common_dec.xml')

root = tree.getroot()

print(root.tag)
SWImpData = root.find("SWImpData")

s = SWImpData.find("DecMessage").find("DecLists")


print(s)
# for i in s:
#     print(i.tag)
#
# s = root.find("{http://www.chinaport.gov.cn/dec}DecLists").find("{http://www.chinaport.gov.cn/dec}DecList")
# print(s)

tree.write('output.xml', encoding="utf-8", xml_declaration=True, method='xml')
