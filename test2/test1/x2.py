# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/8.
# import datetime,os
#
# fi = r'D:\dev\data\loop_server\ftp\clienttmp\DXPENT0000016069_ci1518052471469_test.23353141@szjdintchanged_te'
#
# cur_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
#
# names = os.path.basename(fi).split(".")
# remote_file = names[0] + cur_time + names[1]
#
# print(remote_file)
import datetime
import os
#
# local_update_dir = r'D:\dev\data\loop_server\ftp'
# for name in os.listdir(local_update_dir):
#     file_path = os.path.join(local_update_dir, name)
#     print(file_path)
#     cur_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
#
#     names = os.path.basename(file_path).split(".")
#     remote_file = names[0].split('@')[0] + "@" + cur_time + "." + names[1]
#     print(remote_file)
#
#     # os.rename(file_path,remote_file)


def update(table_name, where=None, **cols):
    """
    :param table_name: 
    :param cols: 
    :param where: 
    :return: 
    """
    filter_condition = ""  # 筛选条件
    if where:
        for k, v in where.items():
            filter_condition += "where {}={}".format(k, v)

    col_vals = []
    for k, v in cols.items():
        col_vals.append("{}={},".format(k, v))
    col_vals = " ".join(col_vals).strip(",")

    sql = 'UPDATE {} SET {} {};'.format(table_name, col_vals, filter_condition)
    print(sql)

d={
    "ClientSeqNo":201712222222222,
    'QpSeqNo':10000111111
}
update("DecMsg",where={"DecId":5},**d)
