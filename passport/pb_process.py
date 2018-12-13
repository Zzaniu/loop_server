import os
import time
import decimal

import datetime
import traceback
from multiprocessing import Process
from threading import Thread

from conf import settings
from utils import log, mail, only_win_pdf, sql
from passport import passport as model_passport

from conf.zipfiles import zip_files

logger = log.getlogger(__name__)


class PBProcess(Process):
    def __init__(self):
        super().__init__()
        self.name = "DB进程-{}".format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))

    def run(self):
        if not settings.DB_TASK:
            return
        while 1:
            try:
                logger.info('%s start' % self.name)
                # self.exec_task()
                t = []
                t.append(Thread(target=self.exec_task))
                t.append(Thread(target=self.exec_task_special))
                for i in t:
                    i.start()
                for i in t:
                    i.join()
                logger.info('%s end' % self.name)
                time.sleep(settings.LOOP_TIME)
            except Exception as e:
                logger.exception(e)
                mail.send_email(text=str(traceback.format_exc()), subject="db线程异常,请火速前往处理")
                logger.warn("db线程异常,以邮件通知")
                time.sleep(settings.EXCEPTION_WAIT_TIME)

    def exec_task(self):
        _Sql = sql.Sql()
        pass_infos = _Sql.select("PRelation", "id", "ClientSeqNo", "DecState", "CreateUser",
                                 where={"DecState": 'TS_RDY', "DeleteFlag": "0"})
        logger.info(pass_infos)
        needed_process_pass = [pass_info for pass_info in pass_infos]
        threads = []
        for pass_info in needed_process_pass:
            # t = Thread(target=self.upload_QP_task, args=(dec_info,))
            t = Thread(target=self.upload_QP_task_pass, args=(pass_info,))
            threads.append(t)

        for i in threads:
            i.start()

        for i in threads:
            i.join()

    def exec_task_special(self):
        _Sql = sql.Sql()
        pass_infos = _Sql.select("SpecialPassPortMsg", "id", "ClientSeqNo", "DecState", "CreateUser",
                                 where={"DecState": 'TS_RDY', "DeleteFlag": "0"})
        logger.info(pass_infos)
        needed_process_pass = [pass_info for pass_info in pass_infos]
        threads = []
        for pass_info in needed_process_pass:
            # t = Thread(target=self.upload_QP_task, args=(dec_info,))
            t = Thread(target=self.upload_QP_task_pass_special, args=(pass_info,))
            threads.append(t)

        for i in threads:
            i.start()

        for i in threads:
            i.join()

    def upload_QP_task_pass(self, pass_info):
        # dec_id = dec_info[1]
        pass_id = pass_info[0]
        ClientSeqNo = pass_info[1]

        _Sql = sql.Sql()
        passport = {}

        # 获取表头数据
        dec_pass_head_fields = ["id", "PId", "SeqNo", "PassportNo", "PassportTypecd", "MasterCuscd", "DclTypecd",
                                "IoTypecd", "BindTypecd", "RltTbTypecd", "RltNo", "AreainOriactNo", "AreainEtpsno",
                                "AreainEtpsNm", "AreainEtpsSccd", "VehicleNo", "VehicleIcNo", "ContainerNo",
                                "VehicleWt", "VehicleFrameNo", "VehicleFrameWt", "ContainerType", "ContainerWt",
                                "TotalWt", "TotalGrossWt", "TotalNetWt", "DclErConc", "DclEtpsno", "DclEtpsNm",
                                "DclEtpsSccd", "InputCode", "InputSccd", "InputName", "EtpsPreentNo", "Rmk",
                                "DelcareFlag"]

        dec_pass_head_info = _Sql.select("PassPortHead", *dec_pass_head_fields, where={"PId": pass_id})
        passport_id = dec_pass_head_info[0][0]
        h = dict(zip(dec_pass_head_fields, dec_pass_head_info[0]))
        # h['EtpsPreentNo'] = ClientSeqNo
        # 数值型 为0.0000时，赋空值
        # for i in h:
        #     if isinstance(h[i], decimal.Decimal) and not h[i]:
        #         h[i] = ""

        passport['PassPortHead'] = h

        # 获取表体数据
        passport_acmp_fields = ["SeqNo", "PassPortNo", "RltTbTypecd", "RltNo"]
        passport_acmps_info = _Sql.select("PassPortAcmp", *passport_acmp_fields,
                                          where={"Acmp2Head": passport_id, 'DeleteFlag': 0})
        dec_list_list = []
        for passport_acmp_info in passport_acmps_info:
            d = dict(zip(passport_acmp_fields, passport_acmp_info))
            dec_list_list.append(d)

        passport['AcmpList'] = dec_list_list

        xml_file_name = os.path.join(settings.GOLD_XML_DIR, "PassPort" + ClientSeqNo + ".xml")

        # _xml = xml.Xml(xml_file_name,dec) #将dec传入xml然后保存到磁盘先
        _xml = model_passport.Xml(xml_file_name, passport)  # 将dec传入xml然后保存到磁盘先,单一窗口类型
        _xml.save()
        zip_files(xml_file_name)
        logger.info('生成核放单ZIP报文，自编号{}'.format(ClientSeqNo))
        if 1:
            d = {
                "DecState": 'TS_REQ',
            }
            # 更新状态为“草单，申报提交”
            _Sql.update("PRelation", where={"ClientSeqNo": ClientSeqNo, 'DeleteFlag': 0}, **d)
            logger.info('更新PRelation状态为TS_REQ，自编号{}'.format(ClientSeqNo))

    def upload_QP_task_pass_special(self, pass_info):
        # dec_id = dec_info[1]
        pass_id = pass_info[0]
        ClientSeqNo = pass_info[1]

        _Sql = sql.Sql()
        passport = {}

        # 获取表头数据
        dec_pass_head_fields = ["id", "PId", "SeqNo", "PassportNo", "PassportTypecd", "MasterCuscd", "DclTypecd",
                                "IoTypecd", "BindTypecd", "RltTbTypecd", "RltNo", "AreainOriactNo", "AreainEtpsno",
                                "AreainEtpsNm", "AreainEtpsSccd", "VehicleNo", "VehicleIcNo", "ContainerNo",
                                "VehicleWt", "VehicleFrameNo", "VehicleFrameWt", "ContainerType", "ContainerWt",
                                "TotalWt", "TotalGrossWt", "TotalNetWt", "DclErConc", "DclEtpsno", "DclEtpsNm",
                                "DclEtpsSccd", "InputCode", "InputSccd", "InputName", "EtpsPreentNo", "Rmk",
                                "DelcareFlag"]

        dec_pass_head_info = _Sql.select("SpecialPassPortHead", *dec_pass_head_fields, where={"PId": pass_id})
        passport_id = dec_pass_head_info[0][0]
        h = dict(zip(dec_pass_head_fields, dec_pass_head_info[0]))
        # h['EtpsPreentNo'] = ClientSeqNo
        # 数值型 为0.0000时，赋空值
        # for i in h:
        #     if isinstance(h[i], decimal.Decimal) and not h[i]:
        #         h[i] = ""

        passport['PassPortHead'] = h

        # 获取表体数据
        passport_acmp_fields = ["SeqNo", "PassPortNo", "RltTbTypecd", "RltNo"]
        passport_acmps_info = _Sql.select("SpecialPassPortAcmp", *passport_acmp_fields,
                                          where={"PId": pass_id, 'DeleteFlag': 0})
        dec_list_list = []
        for passport_acmp_info in passport_acmps_info:
            d = dict(zip(passport_acmp_fields, passport_acmp_info))
            dec_list_list.append(d)

        passport['AcmpList'] = dec_list_list

        xml_file_name = os.path.join(settings.GOLD_XML_DIR, "SpecialPassPort" + ClientSeqNo + ".xml")

        # _xml = xml.Xml(xml_file_name,dec) #将dec传入xml然后保存到磁盘先
        _xml = model_passport.Xml(xml_file_name, passport)  # 将dec传入xml然后保存到磁盘先,单一窗口类型
        _xml.save()
        zip_files(xml_file_name)
        logger.info('生成核放单ZIP报文，自编号{}'.format(ClientSeqNo))
        if 1:
            d = {
                "DecState": 'TS_REQ',
            }
            # 更新状态为“草单，申报提交”
            _Sql.update("SpecialPassPortMsg", where={"ClientSeqNo": ClientSeqNo, 'DeleteFlag': 0}, **d)
            logger.info('更新SpecialPassPortMsg状态为TS_REQ，自编号{}'.format(ClientSeqNo))
