import time
import decimal

import datetime
import traceback
from multiprocessing import Process
from threading import Thread

from conf import settings
from tainvt import tawsinvt
from utils import log, mail, sql

logger = log.getlogger(__name__)


class TaBProcess(Process):
    def __init__(self):
        super().__init__()
        self.name = "DB进程-{}".format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))

    def run(self):
        if not settings.DB_TASK:
            return
        while 1:
            try:
                logger.info('%s start' % self.name)
                self.exec_task()
                logger.info('%s end' % self.name)
                time.sleep(settings.LOOP_TIME)
            except Exception as e:
                logger.exception(e)
                mail.send_email(text=str(traceback.format_exc()), subject="db线程异常,请火速前往处理")
                logger.warn("db线程异常,以邮件通知")
                time.sleep(settings.EXCEPTION_WAIT_TIME)

    def exec_task(self):
        _Sql = sql.Sql()
        dec_infos = _Sql.select("TAMsg", "id", "ClientSeqNo", "DecState", "CreateUser",
                                where={"DecState": 'TS_RDY', "DeleteFlag": "0"})

        logger.info(dec_infos)

        # 先全部取出来
        needed_process_decs = [dec_info for dec_info in dec_infos]

        threads = []
        for dec_info in needed_process_decs:
            t = Thread(target=self.upload_QP_task, args=(dec_info,))
            threads.append(t)

        for i in threads:
            i.start()

        for i in threads:
            i.join()

    def upload_QP_task(self, dec_info):
        """
        将报关单提交到QP的任务
        :param dec_info: 报关单信息,是一个元组,内容:("DecId", "ClientSeqNo", "DecState", "CreateUser")
        :return: 
        """
        dec_id = dec_info[0]
        ClientSeqNo = dec_info[1]

        _Sql = sql.Sql()
        dec = {}

        # 获取表头数据
        dec_head_fields = ["id", "BONDINVTNO", "SEQNO", "PUTRECNO", "ETPSINNERINVTNO", "RLTENTRYBIZOPETPSSCCD",
                           "RLTENTRYBIZOPETPSNO", "RLTENTRYBIZOPETPSNM", "RCVGDETPSNO", "RVSNGDETPSSCCD", "RCVGDETPSNM",
                           "DCLETPSSCCD", "DCLETPSNO", "DCLETPSNM", "INVTDCLTIME", "ENTRYNO", "RLTINVTNO",
                           "RLTPUTRECNO", "RLTENTRYNO", "RLTENTRYBIZOPETPSSCCD", "RLTENTRYBIZOPETPSNO",
                           "RLTENTRYBIZOPETPSNM", "RLTENTRYRVSNGDETPSSCCD", "RLTENTRYRCVGDETPSNO",
                           "RLTENTRYRCVGDETPSNM", "RLTENTRYDCLETPSSCCD", "RLTENTRYDCLETPSNO", "RLTENTRYDCLETPSNM",
                           "IMPEXPPORTCD", "DCLPLCCUSCD", "IMPEXPMARKCD", "MTPCKENDPRDMARKCD", "SUPVMODECD",
                           "TRSPMODECD", "DCLCUSFLAG", "DCLCUSTYPECD", "VRFDEDMARKCD", "APPLYNO",
                           "LISTTYPE", "INPUTCODE", "INPUTCREDITCODE", "INPUTNAME", "ICCARDNO", "INPUTTIME", "LISTSTAT",
                           "CORRENTRYDCLETPSSCCD", "CORRENTRYDCLETPSNO", "CORRENTRYDCLETPSNM", "DECTYPE",
                           "STSHIPTRSARVNATCD", "BONDINVTTYPECD", "Rmk", "TAId", "DelcareFlag", 'BIZOPETPSNO',
                           'BIZOPETPSSCCD', 'BIZOPETPSNM']

        dec_head_info = _Sql.select("TradeAccountInvtHeadType", *dec_head_fields, where={"TAId": dec_id})

        h = dict(zip(dec_head_fields, dec_head_info[0]))
        h['INVTDCLTIME'] = h['INVTDCLTIME'].strftime("%Y%m%d")
        h['INPUTTIME'] = h['INPUTTIME'].strftime("%Y%m%d")
        # h['ETPSINNERINVTNO'] = ClientSeqNo

        # 数值型 为0.0000时，赋空值
        for i in h:
            if isinstance(h[i], decimal.Decimal) and not h[i]:
                h[i] = ""

        dec['DecHead'] = h

        # 获取表体数据
        dec_list_fields = ["id", "SEQNO", "GDSSEQNO", "PUTRECSEQNO", "GDSMTNO", "GDECD", "GDSNM", "GDSSPCFMODELDESC",
                           "DCLUNITCD", "LAWFUNITCD", "SECDLAWFUNITCD", "NATCD", "DCLUPRCAMT", "DCLTOTALAMT",
                           "USDSTATTOTALAMT", "DCLCURRCD", "LAWFQTY", "SECDLAWFQTY", "WTSFVAL", "FSTSFVAL", "SECDSFVAL",
                           "DCLQTY", "GROSSWT", "NETWT", "USECD", "LVYRLFMODECD", "UCNSVERNO", "ENTRYGDSSEQNO",
                           "FLOWAPPLYTBSEQNO", "APPLYTBSEQNO", "Rmk", "TAId"]
        dec_lists_info = _Sql.select("TradeAccountInvtListType", *dec_list_fields,
                                     where={"TAId": dec_id, 'DeleteFlag': 0})
        dec_list_list = []
        for dec_list_info in dec_lists_info:
            d = dict(zip(dec_list_fields, dec_list_info))

            for i in d:
                if isinstance(d[i], decimal.Decimal) and not d[i]:
                    d[i] = ""

            dec_list_list.append(d)
        dec['DecLists'] = dec_list_list

        import os
        xml_file_name = os.path.join(settings.GOLD_XML_DIR, "TAInvt" + ClientSeqNo + ".xml")

        _xml = tawsinvt.Xml(xml_file_name, dec)  # 将dec传入xml然后保存到磁盘先,单一窗口类型

        _xml.save()
        from conf.zipfiles import zip_files
        zip_files(xml_file_name)
        logger.info('生成加贸账册核注清单ZIP报文，自编号{}'.format(ClientSeqNo))
        if settings.DEBUG:
            d = {
                "DecState": 'TS_REQ',
            }
            # 更新状态为“草单，申报提交”
            _Sql.update("TAMsg", where={"ClientSeqNo": ClientSeqNo, 'DeleteFlag': 0}, **d)
            logger.info('更新TAMsg状态为TS_REQ，自编号{}'.format(ClientSeqNo))


if __name__ == "__main__":
    ta_db = TaBProcess()
    ta_db.start()  # start会自动调用run
