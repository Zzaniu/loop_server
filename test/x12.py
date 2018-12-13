# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/5.


def f1():
    fields = ['ClassMark',
                  'CodeTS',
                  'ContrItem',
                  'DeclPrice',
                  'DutyMode',
                  'Factor',
                  'GModel',
                  'GName',
                  'GNo',
                  'OriginCountry',
                  'TradeCurr',
                  'DeclTotal',
                  'GQty',
                  'FirstQty',
                  'SecondQty',
                  'GUnit',
                  'FirstUnit',
                  'SecondUnit',
                  'UseTo',
                  'WorkUsd',
                  'ExgNo',
                  'ExgVersion',
                  'DestinationCountry',
              ]

    for i, k in enumerate(fields):
        print('"{}",'.format(k.strip()), end=" ")

        if i != 0 and i % 6 == 0:
            print()


def f2():
    ss = """
DecListId DecId GNo GoodsId ClassMark CodeTs ContrItem 
DeclPrice DutyMode Factor GModel GName OriginCountry 
TradeCurr DeclTotal GQty FirstQty SecondQty GUnit 
FirstUnit SecondUnit UseTo WorkUsd ExgNo ExgVersion 
DestinationCountry 
    """
    for i, k in enumerate(ss.split()):
        print('"{}",'.format(k.strip()), end=" ")

        if i != 0 and i % 6 == 0:
            print()


def f3():
    sss="""ClassMark
CodeTS
ContrItem
DeclPrice
DutyMode
Factor
GModel
GName
GNo
OriginCountry
TradeCurr
DeclTotal
GQty
FirstQty
SecondQty
GUnit
FirstUnit
SecondUnit
UseTo
WorkUsd
ExgNo
ExgVersion
DestinationCountry
    """
    l = sss.split("\n")
    li=[]
    for i in l:
        s = i.strip("\n")
        s = i.strip(" ")
        li.append(s)

    for i, k in enumerate(li):
        print('"{}",'.format(k.strip()), end=" ")

        if i != 0 and i % 6 == 0:
            print()



if __name__ == '__main__':
    f3()
