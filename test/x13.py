

# import datetime
#
# a = "2017-12-05 10:12:01"
# b = "2017-12-05 10:12:31"
#
# a = datetime.datetime.strptime(a,"%Y-%m-%d %H:%M:%S")
# print(a)
#
# b = datetime.datetime.strptime(b,"%Y-%m-%d %H:%M:%S")
# print(b)
#
# print(a<b)
import datetime
import os
import re


def handle_files_order(files):
    """将回执按照生成时间dDate排序，需要打开文件获取内容"""

    receipt_files = []
    other_files = []

    for file_path in files:
        file_name = os.path.basename(file_path)
        if "Receipt" in file_name:
            receipt_files.append(file_path)
        else:
            other_files.append(file_path)

    receipt_files_dict = {}
    for file_path in receipt_files:
        with open(file_path,encoding="utf-8") as f:
            content = f.read()
            ret = re.search(r"<dDate>(.*?)</dDate>", content)
            if ret:
                dDate = ret.group(1)
                receipt_files_dict[file_path] = datetime.datetime.strptime(dDate, "%Y-%m-%d %H:%M:%S")

    s = sorted(receipt_files_dict.items(), key=lambda x: x[1])

    print(s)

    b = [i[0] for i in s]

    print(b)


if __name__ == '__main__':
    RECEIPT_INOBXMOVE = r"C:\ImpPath\Dec\InBoxMove"
    client_tmp_files = os.listdir(RECEIPT_INOBXMOVE)
    file_path = [os.path.join(RECEIPT_INOBXMOVE, i) for i in client_tmp_files]

    # print(client_tmp_files)
    handle_files_order(file_path)