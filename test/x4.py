# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/5.

import os
import time
BASE_DIR = os.path.abspath(__file__)

file_path = os.path.join(BASE_DIR,"a.log")

f = open(file_path,mode="a",encoding="utf-8")

for i in range(10):
    f.write(i)
    time.sleep(1)