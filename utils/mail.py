# !/usr/bin/env python
# coding: utf-8
# created by leiyangs on 2018/2/5.

import re
import smtplib
import email.mime.multipart
import email.mime.text
from email.utils import formataddr

from conf.settings import SEND_EMAIL, EMAIL_PWD
from . import log
logger = log.getlogger(__name__)


def send_email(text,subject):
    """
    发送邮件
    :param text: 需要发送的html格式的字符串
    :param subject: 发邮件的主题
    :return: 
    """
    # to_email = 'Michael.song@betterbt.com,zaniu.zeng@betterbt.com'
    to_email = 'zaniu.zeng@betterbt.com'
    smtp_server = 'smtp.126.com'

    msg = email.mime.multipart.MIMEMultipart()
    msg['from'] = formataddr(['ZzaniuzzZ', SEND_EMAIL])
    msg['to'] = to_email
    msg['subject'] = subject

    content = text
    txt = email.mime.text.MIMEText(content, _charset='utf-8')
    msg.attach(txt)

    try:
        smtp = smtplib.SMTP(smtp_server, 25)
        smtp.set_debuglevel(1)
        smtp.login(SEND_EMAIL, EMAIL_PWD)
        smtp.sendmail(SEND_EMAIL, to_email.split(','), str(msg))
        smtp.quit()
    except Exception as e:
        logger.exception(e)
        logger.error("邮件发送异常,极有可能是邮件发送功能被禁止.")


def send_email_qq(text,subject):
    """
    发送邮件
    :param text: 需要发送的字符串
    :param subject: 发邮件的主题
    :return: 
    """
    from_email = '2673460873@qq.com'
    password = 'jbdyaaiolwqgdjjf'  # 请注意这里并不是qq邮箱的登录密码,是授权码,授权码是用于登录第三方邮件客户端的专用密码。
    # to_email = '472093743@qq.com'
    to_email = 'Michael.song@betterbt.com,zaniu.zeng@betterbt.com,devcyx.chen@betterbt.com'
    # to_email = 'Michael.song@betterbt.com'
    smtp_server = 'smtp.qq.com'

    msg = email.mime.multipart.MIMEMultipart()
    msg['from'] = from_email
    msg['to'] = to_email
    msg['subject'] = subject

    content = text
    txt = email.mime.text.MIMEText(content, _charset='utf-8')
    msg.attach(txt)

    try:
        smtp = smtplib.SMTP_SSL(smtp_server,465)
        smtp.set_debuglevel(1)
        smtp.login(from_email, password)
        smtp.sendmail(from_email, to_email.split(','), msg.as_string())
        smtp.quit()
    except Exception as e:
        logger.exception(e)
        logger.error("邮件发送异常,极有可能是邮件发送功能被禁止.")


if __name__ == '__main__':
    try:
        a = 3/0
    except Exception as e:
        import traceback
        send_email(text=str(traceback.format_exc()), subject="db线程异常,请火速前往处理")

