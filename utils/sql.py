import time
import traceback
import pymysql
from DBUtils.PooledDB import PooledDB
import functools
import threading

from conf import settings
from utils import log
log = log.getlogger(__name__)


def singleton(func):
    """线程安全的单例装饰器函数"""
    data = {'obj': None}
    _lock = threading.Lock()

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with _lock:
            if data.get('obj') is None:
                data['obj'] = func(*args, **kwargs)
        return data['obj']
    return wrapper


@singleton
class singletonPoolDB(PooledDB):
    """单例数据库连接池"""
    pass


class Sql(object):
    def __init__(self):
        self.__pool = self.connect_mysql()
        self.conn = self.__pool.connection()
        self.cursor = self.conn.cursor()

    def __del__(self):
        """退出时释放资源"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    @staticmethod
    def connect_mysql():
        """单例模式，防止创建多个连接池"""
        times = settings.RE_CONNECT_SQL_TIME
        while times > 0:
            try:
                # 初始化时，链接池中至少创建的空闲的链接，0表示不创建
                # 链接池中最多闲置的链接，0和None不限制
                # 链接池中最多共享的链接数量，0和None表示全部共享。PS: 无用，因为pymysql和MySQLdb等模块的 threadsafety都为1，所有值无论设置为多少，_maxshared永远为0，所以永远是所有链接都共享。
                # 连接池允许的最大连接数，0和None表示不限制连接数
                # 连接池中如果没有可用连接后，是否阻塞等待。True，等待；False，不等待然后报错
                # 一个链接最多被重复使用的次数，None表示无限制
                _pool = singletonPoolDB(pymysql, mincached=5, maxcached=5, maxshared=0, maxconnections=20,
                                        blocking=True, maxusage=None, **settings.DATABASES)
                return _pool
            except:
                log.debug('创建连接池失败，暂停{}S后继续创建'.format(settings.RE_CONNECT_SQL_WAIT_TIME))
                print('创建连接池失败，暂停{}S后继续创建'.format(settings.RE_CONNECT_SQL_WAIT_TIME))
                times -= 1
                time.sleep(settings.RE_CONNECT_SQL_WAIT_TIME)

        log.error('数据库连接失败...')
        raise Exception('数据库连接失败...')

    def insert(self, table_name, **kwargs):
        keys, vals = tuple(kwargs.keys()), tuple(kwargs.values())
        cols = ",".join(keys)
        wildcards = ",".join(["%s" for i in range(len(vals))])
        sql = 'insert into {}({}) VALUES ({});'.format(table_name, cols, wildcards)
        try:
            self.cursor.execute(sql, args=vals)
            self.conn.commit()
            return True
        except:
            log.error('数据库发生错误，错误信息{}'.format(str(traceback.format_exc())))
            self.conn.rollback()
            return False

    def update(self, table_name, where=None, **kwargs):
        """
        :param table_name: 
        :param cols: 
        :param where: 
        :return: 
        """
        assert (where is not None), "Update 的时候请带上where条件，如需更新所有，请使用raw_sql..."
        filter_condition = ""  # 筛选条件
        vals_condition = tuple()
        if where:
            vals_condition = tuple(where.values())
            for i, k in enumerate(where):
                if len(vals_condition) == 1:
                    filter_condition += '{}=%s'.format(k)
                else:
                    if i == 0:
                        filter_condition += '{}=%s'.format(k)
                    else:
                        filter_condition += ' and {}=%s'.format(k)

        # col_vals = []
        # for k, v in cols.items():
        #     col_vals.append("{}={},".format(k, v))
        # col_vals = " ".join(col_vals).strip(",")

        keys, vals = tuple(kwargs.keys()), tuple(kwargs.values())
        cols = ",".join(keys)
        wildcards = ",".join(["{}=%s".format(keys[i]) for i in range(len(vals))])

        sql = 'UPDATE {} SET {} where {};'.format(table_name, wildcards, filter_condition)

        # 将筛选条件的val加到tuple
        vals = vals + vals_condition
        try:
            ret = self.cursor.execute(sql, args=vals)  # 受影响的行
            self.conn.commit()
            if ret:
                return True
            else:
                return False
        except:
            self.conn.rollback()
            log.error('数据库发生错误，错误信息{}'.format(str(traceback.format_exc())))
            return False

    def select(self, table_name, *cols, where=None, limit=None):
        """
        :param table_name: 表名,str
        :param cols: 列名
        :param where: 筛选条件,暂时只添加一个
        :param limit: 查询行数,int型,None表示查询苏所有
        SELECT * FROM DecMsg where ClientSeqNo="201801100950223990" and DeleteFlag="0"
        :return: 
        """
        filter_condition = "where "  # 筛选条件,暂时只支持一个查询条件
        vals = tuple()
        if where:
            vals = tuple(where.values())
            for i, k in enumerate(where):

                if len(vals) == 1:
                    filter_condition += '{}=%s'.format(k)
                else:
                    if i == 0:
                        filter_condition += '{}=%s'.format(k)
                    else:
                        filter_condition += ' and {}=%s'.format(k)

        if not cols and not limit:  # select * ,无limit
            sql = 'select * from {} {};'.format(table_name, filter_condition)
        elif limit:
            if not cols:  # select * 有limit
                sql = 'select * from {} {} limit {};'.format(table_name, filter_condition, limit)
            else:  # select x1,x2 有limit
                col_names = ",".join(cols)
                sql = 'select {} from {} {} limit {};'.format(col_names, table_name, filter_condition, limit)
        else:
            # no limit,有col值
            col_names = ",".join(cols)
            sql = 'select {} from {} {};'.format(col_names, table_name, filter_condition)

        self.cursor.execute(sql, vals)
        self.conn.commit()
        return self.cursor.fetchall()

    def raw_sql(self, _sql):
        """支持原生SQL"""
        ret = {'status': False, 'ret_tuples': ()}
        try:
            lines = self.cursor.execute(_sql)
            self.conn.commit()
            if lines:
                ret['status'] = True
                if _sql.lower().startswith('select'):
                    ret['ret_tuples'] = self.cursor.fetchall()
                    log.debug("ret['ret_tuples'] = {}".format(ret['ret_tuples']))
        except Exception as e:
            self.conn.rollback()
            log.error('error = {}'.format(e))

        return ret


if __name__ == "__main__":
    sql = Sql()
    # id = sql.select('DecMsg', 'decid', 'QpNotes', where={"DecId": 772})
    # print("id = ", id)
    # for _id in id:
    #     # sql.update('DecMsg', where={'decid': _id[0]}, DecState='TS_INI')
    #     print('_id = ', _id[1])
    # print('decid = ', id)
    a = sql.select('Msg', 'TMId', 'TAId', 'DecId', where={'NId': 564, 'id': 66})
    for _a in a:
        tmid, taid, decid = _a
        print('tmid = {}, taid = {}, decid = {}'.format(tmid, taid, decid))
        if taid:
            print('大爷好')
    a = sql.update('DecMsg', where={'DecId': 50, 'DecState': 'ts_ini'}, QpNotes='大爷好走')
    print('a = ', a)

    sql_str = "select d.DecId, d.QpNotes from Decmsg as d where d.Decid between 50 and 60"
    ret = sql.raw_sql(sql_str)
    print("ret = ", ret)
