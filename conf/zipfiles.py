import zipfile
import os
from conf import settings


def zip_files(xml_file_name):
    """在中间文件夹压缩XML文件至发送文件夹"""
    new_xml_file_name = xml_file_name.split('\\')[-1]
    zip_file_name = os.path.join(settings.GOLD_DATA_SEND_DIR, new_xml_file_name.replace('.xml', '.zip'))
    f_zip = zipfile.ZipFile(zip_file_name, 'w', zipfile.ZIP_DEFLATED)
    f_zip.write(xml_file_name, new_xml_file_name)
    f_zip.close()
    # 删除XML文件
    os.remove(xml_file_name)
