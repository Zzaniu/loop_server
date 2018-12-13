# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/5.

# 主进程代码运行完毕,守护进程就会结束
from multiprocessing import Process
from threading import Thread
import time


def foo():
    print(123)
    time.sleep(100)
    print("end123")


# def bar():
#     print(456)
#     time.sleep(3)
#     print("end456")


if __name__ == '__main__':
    p1 = Process(target=foo)
    # p2 = Process(target=bar)

    # p1.daemon = True
    p1.start()
    # p2.start()



    print("main-------")  # 打印该行则主进程代码结束,则守护进程p1应该被终止,可能会有p1任务执行的打印信息123,因为主进程打印main----时,p1也执行了,但是随即被终止
    time.sleep(5)
    print("我已经执行完毕")
    p1.terminate()

    time.sleep(2)

    print("p1的状态:",p1.is_alive())


