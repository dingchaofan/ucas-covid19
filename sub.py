"""
author: Les1ie
mail: me@les1ie.com
license: CC BY-NC-SA 3.0
"""
import os
import json
import pytz
import hashlib
import smtplib
import requests
from time import sleep
from pathlib import Path
from random import randint
from datetime import datetime
from email.utils import formataddr
from email.mime.text import MIMEText

# 开启debug将会输出打卡填报的数据，关闭debug只会输出打卡成功或者失败，如果使用github actions，请务必设置该选项为False
debug = False

# 忽略网站的证书错误，这很不安全 :(
verify_cert = False

# 全局变量
user = "USERNAME"
passwd = "PASSWORD"
api_key = "API_KEY"

smtp_port = "SMTP_PORT"
smtp_server = "SMTP_SERVER"
sender_email = "SENDER_EMAIL"
sender_email_passwd = "SENDER_EMAIL_PASSWD"
receiver_email = "RECEIVER_EMAIL"

# 如果检测到程序在 github actions 内运行，那么读取环境变量中的登录信息
if os.environ.get('GITHUB_RUN_ID', None):
    user = os.environ['SEP_USER_NAME']  # sep账号
    passwd = os.environ['SEP_PASSWD']  # sep密码
    api_key = os.environ['API_KEY']  # server酱的api，填了可以微信通知打卡结果，不填没影响

    smtp_port = os.environ['SMTP_PORT']  # 邮件服务器端口，默认为qq smtp服务器端口
    smtp_server = os.environ['SMTP_SERVER']  # 邮件服务器，默认为qq smtp服务器
    sender_email = os.environ['SENDER_EMAIL']  # 发送通知打卡通知邮件的邮箱
    sender_email_passwd = os.environ['SENDER_EMAIL_PASSWD']  # 发送通知打卡通知邮件的邮箱密码
    receiver_email = os.environ['RECEIVER_EMAIL']  # 接收打卡通知邮件的邮箱


def login(s: requests.Session, username, password, cookie_file: Path):
    # r = s.get(
    #     "https://app.ucas.ac.cn/uc/wap/login?redirect=https%3A%2F%2Fapp.ucas.ac.cn%2Fsite%2FapplicationSquare%2Findex%3Fsid%3D2")
    # print(r.text)

    if cookie_file.exists():
        cookie = json.loads(cookie_file.read_text())
        s.cookies = requests.utils.cookiejar_from_dict(cookie)
        # 测试cookie是否有效
        if get_daily(s) == False:
            print("cookie失效，进入登录流程")
        else:
            print("cookie有效，跳过登录环节")
            return

    payload = {
        "username": username,
        "password": password
    }
    r = s.post("https://app.ucas.ac.cn/uc/wap/login/check", data=payload)

    # print(r.text)
    if r.json().get('m') != "操作成功":
        print("登录失败")
        message(api_key, sender_email, sender_email_passwd, receiver_email, "健康打卡登录失败", "登录失败")

    else:
        print("登录成功")
        with open(cookie_file, 'w', encoding='u8') as f:
            f.write(json.dumps(requests.utils.dict_from_cookiejar(r.cookies)))
            print("cookies 保存完成，文件名为 {}".format(cookie_file))


def get_daily(s: requests.Session):
    daily = s.get("https://app.ucas.ac.cn/ncov/api/default/daily?xgh=0&app_id=ucas")
    # info = s.get("https://app.ucas.ac.cn/ncov/api/default/index?xgh=0&app_id=ucas")
    if '操作成功' not in daily.text:
        # 会话无效，跳转到了登录页面
        print("会话无效")
        return False

    j = daily.json()
    return j.get('d') if j.get('d', False) else False


def submit(s: requests.Session, old: dict):
    new_daily = {
        'realname': old['realname'],
        'number': old['number'],
        'szgj_api_info': old['szgj_api_info'],
        'szgj': old['szgj'],
        'old_sfzx': old['sfzx'],
        'sfzx': old['sfzx'],
        'szdd': old['szdd'],
        'ismoved': 0,  # 如果前一天位置变化这个值会为1，第二天仍然获取到昨天的1，而事实上位置是没变化的，所以置0
        # 'ismoved': old['ismoved'],
        'tw': old['tw'],
        'bztcyy': old['bztcyy'],
        # 'sftjwh': old['sfsfbh'],  # 2020.9.16 del
        # 'sftjhb': old['sftjhb'],  # 2020.9.16 del
        'sfcxtz': old['sfcxtz'],
        'sfyyjc': old['sfyyjc'],
        'jcjgqr': old['jcjgqr'],
        # 'sfjcwhry': old['sfjcwhry'],  # 2020.9.16 del
        # 'sfjchbry': old['sfjchbry'],  # 2020.9.16 del
        'sfjcbh': old['sfjcbh'],
        'jcbhlx': old['jcbhlx'],
        'sfcyglq': old['sfcyglq'],
        'gllx': old['gllx'],
        'sfcxzysx': old['sfcxzysx'],
        'old_szdd': old['szdd'],
        'geo_api_info': old['old_city'],  # 保持昨天的结果
        'old_city': old['old_city'],
        'geo_api_infot': old['geo_api_infot'],
        'date': datetime.now(tz=pytz.timezone("Asia/Shanghai")).strftime("%Y-%m-%d"),
        'fjsj': old['fjsj'],  # 返京时间
        'ljrq': old['ljrq'],  # 离京日期 add@2021.1.24
        'qwhd': old['qwhd'],  # 去往何地 add@2021.1.24
        'chdfj': old['chdfj'],  # 从何地返京 add@2021.1.24
        'jcbhrq': old['jcbhrq'],
        'glksrq': old['glksrq'],
        'fxyy': old['fxyy'],
        'jcjg': old['jcjg'],
        'jcjgt': old['jcjgt'],
        'qksm': old['qksm'],
        'remark': old['remark'],
        'jcjgqk': old['jcjgqk'],
        'jcwhryfs': old['jcwhryfs'],
        'jchbryfs': old['jchbryfs'],
        'gtshcyjkzt': old['gtshcyjkzt'],  # add @2020.9.16
        'jrsfdgzgfxdq': old['jrsfdgzgfxdq'],  # add @2020.9.16
        'jrsflj': old['jrsflj'],  # add @2020.9.16
        'app_id': 'ucas'
    }

    check_data_msg = check_submit_data(new_daily)  # 检查上报结果
    if check_data_msg is not None:
        message(api_key, sender_email, sender_email_passwd, receiver_email, "每日健康打卡-{}".format(check_data_msg),
                "{}".format(new_daily))
        print("提交数据存在问题，请手动打卡，问题原因： {}".format(check_data_msg))
        return

    r = s.post("https://app.ucas.ac.cn/ncov/api/default/save", data=new_daily)
    if debug:
        from urllib.parse import parse_qs, unquote
        print("昨日信息:", json.dumps(old, ensure_ascii=False, indent=2))
        print("提交信息:",
              json.dumps(parse_qs(unquote(r.request.body), keep_blank_values=True), indent=2, ensure_ascii=False))

    result = r.json()
    if result.get('m') == "操作成功":
        print("打卡成功")
    else:
        print("打卡失败，错误信息: ", r.json().get("m"))

    message(api_key, sender_email, sender_email_passwd, receiver_email, result.get('m'), new_daily)


def check_submit_data(data: dict):
    """
    检查提交数据是否正常
    """
    msg = []
    # 所在地点
    if data['szdd'] != "国内":
        msg.append("所在地点不是国内，请手动填报")

    # 体温
    if int(data['tw']) > 4:
        msg.append("体温大于 37.3 度 ，请手动填报")

    return ";".join(msg) if msg else None


def message(key, sender, mail_passwd, receiver, subject, msg):
    """
    再封装一下 :) 减少调用通知写的代码
    """
    if api_key != "":
        server_chan_message(key, subject, msg)
    if sender_email != "" and receiver_email != "":
        send_email(sender, mail_passwd, receiver, subject, msg)


def server_chan_message(key, title, body):
    """
    微信通知打卡结果
    """
    # 错误的key也可以发送消息，无需处理 :)
    msg_url = "https://sctapi.ftqq.com/{}.send?title={}&desp={}".format(key, title, body)
    requests.get(msg_url)


def send_email(sender, mail_passwd, receiver, subject, msg):
    """
    邮件通知打卡结果
    """
    try:
        body = MIMEText(str(msg), 'plain', 'utf-8')
        body['From'] = formataddr(["notifier", sender])
        body['To'] = formataddr(["me", receiver])
        body['Subject'] = "UCAS疫情填报助手通知-" + subject

        global smtp_port, smtp_server
        if smtp_server == "" or smtp_port == "":
            smtp_port = 465
            smtp_server = "smtp.qq.com"
        smtp = smtplib.SMTP_SSL(smtp_server, smtp_port)
        smtp.login(sender, mail_passwd)
        smtp.sendmail(sender, receiver, body.as_string())
        smtp.quit()
        print("邮件发送成功")
    except Exception as ex:
        print("邮件发送失败")
        if debug:
            print(ex)


def report(username, password):
    s = requests.Session()
    s.verify = verify_cert  # 不验证证书
    header = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 \
        Chrome/78.0.3904.62 XWEB/2693 MMWEBSDK/201201 Mobile Safari/537.36 MMWEBID/1300 \
        MicroMessenger/7.0.22.1820 WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64"
    }
    s.headers.update(header)

    print(datetime.now(tz=pytz.timezone("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S %Z"))
    for i in range(randint(10, 600), 0, -1):
        print("\r等待{}秒后填报".format(i), end='')
        sleep(1)

    cookie_file_name = Path("{}.json".format(hashlib.sha512(username.encode()).hexdigest()[:8]))
    login(s, username, password, cookie_file_name)
    yesterday = get_daily(s)
    submit(s, yesterday)


if __name__ == "__main__":
    report(username=user, password=passwd)
