# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/5.

import multiprocessing
import time
import signal


def child():
    i = 1
    while 1:
        print(i)

        time.sleep(2)
        i = i + 1


if __name__ == "__main__":
    p = multiprocessing.Process(target=child)
    p.daemon = True
    p.start()


    def sigchld_handler(signum, frame):
        print( "Child process quit whith signal " + str(signum))

        p = multiprocessing.Process(target=child)
        p.daemon = True
        p.start()


    signal.signal(signal.SIGCHLD, sigchld_handler)
    while 1:
        signal.pause()