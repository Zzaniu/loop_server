# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/5.

import os
import sys

path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, path)

if __name__ == '__main__':
    from src.script import Auto_Run
    Auto_Run()
