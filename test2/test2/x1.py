# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/10.

# if "T" in NoticeDate:  # 20180208T09152600
#     NoticeDate = NoticeDate[:8] + NoticeDate[9:-2]
#
# print(NoticeDate)

# f = r"C:\BTCS\mdn_tmp\DXPENT0000016068test@20180210203032.23353192@szjdintchanged_te"
# import os
# s = os.path.basename(f)
# print(s)
import re
# content="<Data>fdsafdsfdsf</Data>"
# ret = re.search(r"<Data>(.*?)</Data>", content)
# s = ret.group(1)
# print(s)

sss="""
<?xml version="1.0" encoding="GB2312"?>
<DEC_DATA>
<DEC_RESULT>
<SEQ_NO>000000001398639573</SEQ_NO>
<ENTRY_ID></ENTRY_ID>
<NOTICE_DATE>20180208T15032200</NOTICE_DATE>
<CHANNEL>7</CHANNEL>
<NOTE>Z11000001308087512直接申报成功</NOTE>
<DECL_PORT>5317</DECL_PORT>
<AGENT_NAME></AGENT_NAME>
<DECLARE_NO></DECLARE_NO>
<TRADE_CO></TRADE_CO>
<CUSTOMS_FIELD></CUSTOMS_FIELD>
<BONDED_NO></BONDED_NO>
<I_E_DATE></I_E_DATE>
<PACK_NO></PACK_NO>
<BILL_NO></BILL_NO>
<TRAF_MODE></TRAF_MODE>
<VOYAGE_NO></VOYAGE_NO>
<NET_WT></NET_WT>
<GROSS_WT></GROSS_WT>
<D_DATE></D_DATE>
</DEC_RESULT>
<RESULT_INFO></RESULT_INFO>
</DEC_DATA>
"""
s=re.search(r"<NOTICE_DATE>(.*?)</NOTICE_DATE>",sss)
ret = s.group(1)
print(ret)
print(type(ret))
print(s.group(1))
import shutil

# dt='C:\BTCS\clienttmp\DXPENT0000016069testxxxxxxx@20180210203042.23353192@szjdintchanged_te'
# src=r"C:\BTCS\clienttmp_tmp\DXPENT0000016069testxxxxxxx@20180210203042.23353192@szjdintchanged_te"
# shutil.move(src, dt)  # 移动文件
#
# s="2018-02-08T13:39:34.973+08:00"
# s = s[:-6].replace("T"," ")[:19]
# # print(s)
# #
# import datetime
# delta = datetime.timedelta(hours=8)
# s = (datetime.datetime.strptime(s,"%Y-%m-%d %H:%M:%S")+delta).strftime("%Y%m%d%H%M%S")
# print(s)
# # datetime.datetime.strftime(s,"")

# NoticeDate = '20180208T154034'
#               # 201802081540
# NoticeDate = NoticeDate[:8] + NoticeDate[9:-2]
# print(NoticeDate)