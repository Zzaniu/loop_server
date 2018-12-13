# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/5.
import os
import re
from xml.etree import ElementTree as ET

import copy

from conf.settings import BASE_DIR

template_path = os.path.join(BASE_DIR, "newsinvt", "NewsInvt201806291610593390.xml")  # xml模板路径
tree = ET.parse(template_path)
root = tree.getroot()

# self.DecList = self.root.find('Object/Package/DataInfo/BussinessData/InvtMessage/InvtListType')
DecLists = root.find("Object/Package/DataInfo/BussinessData/InvtMessage")
if DecLists.findall("InvtListType"):
    print(11)
# DecLists.remove(DecLists)


