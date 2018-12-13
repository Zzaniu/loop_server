# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/5.

from xml.etree import ElementTree as ET



ET.register_namespace('', "http://www.chinaport.gov.cn/dec")
ET.register_namespace('xsd', "http://www.w3.org/2001/XMLSchema")

ET.register_namespace('xsi', "http://www.w3.org/2001/XMLSchema-instance")

tree = ET.parse('Dec201802011651490001.xml')

root = tree.getroot()
s = root.find("{http://www.chinaport.gov.cn/dec}DecLists")
s = root.find("{http://www.chinaport.gov.cn/dec}DecLists").find("{http://www.chinaport.gov.cn/dec}DecList")

tree.write('output.xml', encoding="utf-8", xml_declaration=True, method='xml')
