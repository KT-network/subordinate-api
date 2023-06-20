import hashlib
import re
from threading import Thread

from config import request, db, dbr, Message, mail, app
import dataBase
import json
import time
import random


def _getTime():
    return time.strftime("%H:%M:%S", time.localtime())


def _getTimeDate():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def _getDate():
    return time.strftime("%Y-%m-%d", time.localtime())


def _getTimeInt():
    return time.time()


def _jsonToStr(code=200, data=None):
    info = {'code': code, 'msg': 'succeed' if code == 200 else 'error', 'data': data, 'beFrom': 'Ks',
            'time': _getTimeDate()}
    return json.dumps(info)


# 生成md5字符串
def _getMd5(txt):
    hash_md5 = hashlib.md5()
    txt = txt + '-ks'
    data = txt.encode('utf-8')
    hash_md5.update(data)
    return hash_md5.hexdigest()


# 生成随机数验证码
def _randomCode(num=5):
    s = ''
    for i in range(num):
        s += str(random.randint(0, 9))
    return s


# 邮箱格式判断
def _validateEmail(email):
    if re.match('^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$', email) != None:
        # if re.match('/^\w+@[a-z0-9]+\.[a-z]{2,4}$/', email) != None:
        return True
    else:
        return False


# 发送邮件
def _sendEmail(email, msg):
    def send_async_email(app, msg):
        with app.app_context():
            mail.send(msg)

    msg = Message(subject="谁的部下", recipients=[email], body=msg)
    try:
        Thread(target=send_async_email, args=[app, msg]).start()
        return True
    except:
        return False


# 生成Token
def _generateToken(user, pwd):
    token = _getMd5(user + '-' + pwd + str(_getTimeInt()))
    dbr.set(token, user, ex=18000)
    dbr.set(user, token, ex=18000)
    return token


# 检查token
def _checkToken(token):
    user = dbr.get(token)
    if user is None:
        return -1

    isToken = dbr.get(user)

    if isToken is None:
        return -1

    if token != isToken.decode():
        return -1
    userId = dataBase.User.query.filter_by(user=user.decode()).first()
    if userId is None:
        return -1
    return userId


# 登录
def login_():
    data = request.json

    if 'user' not in data.keys() or 'pwd' not in data.keys():
        return _jsonToStr(code=400, data="缺少参数")

    if '' in data.values() or '' in data.values():
        return _jsonToStr(code=400, data="参数不能为空")

    md5Pwd = _getMd5(data['user'] + "-/-" + data['pwd'])

    users = dataBase.User.query.filter(dataBase.User.user == data['user'],
                                       dataBase.User.passwd == md5Pwd).first()

    if users is None:
        return _jsonToStr(code=400, data="用户不存在或密码错误")
    resData = {}
    devices = []
    for i in users.devices.all():
        info = {}
        info['id'] = i.id
        info['name'] = i.name
        info['devicesId'] = i.devicesId
        info['devicesType'] = i.devicesType
        info['picUrl'] = i.picUrl

        devices.append(info)
    resData['devices'] = devices
    resData['token'] = _generateToken(data['user'], data['pwd'])

    return _jsonToStr(data=resData)


# 注册
def register_():
    data = request.json
    if 'user' not in data.keys() or 'email' not in data.keys() or 'code' not in data.keys() or 'pwd' not in data.keys():
        return _jsonToStr(code=400, data="缺少参数")
    if '' in data.values() or '' in data.values():
        return _jsonToStr(code=400, data="参数不能为空")

    verifyCode = dbr.get(data['code'])
    if verifyCode is None:
        return _jsonToStr(code=400, data="验证码已过期，验证码错误")
    codeData = verifyCode.decode().split("***")
    if codeData[0] != data['user'] or codeData[1] != data['email']:
        return _jsonToStr(code=400, data="验证码已过期，验证码错误")
    try:
        md5Pwd = _getMd5(data['user'] + "-/-" + data['pwd'])
        db.session.add(dataBase.User(user=data['user'], passwd=md5Pwd, email=data['email']))
        db.session.commit()
        dbr.delete(data['code'])
        return _jsonToStr(code=200, data="注册成功")
    except Exception as e:
        return _jsonToStr(code=400, data="注册失败")


# 注册验证码
def register_verifyCode_():
    data = request.json
    if 'user' not in data.keys() or 'email' not in data.keys():
        return _jsonToStr(code=400, data="缺少参数")

    if '' in data.values() or '' in data.values():
        return _jsonToStr(code=400, data="参数不能为空")

    if not _validateEmail(data['email']):
        return _jsonToStr(code=400, data="邮箱格式错误")

    if (len(dataBase.User.query.filter_by(user=data['user']).all()) != 0) or (len(
            dataBase.User.query.filter_by(email=data['email']).all()) != 0):
        return _jsonToStr(code=400, data="账号或邮箱已被注册过")

    code = _randomCode()

    dbr.set(code, data['user'] + "***" + data['email'], ex=300)
    emailMsg = '你正在使用邮箱：' + data['email'] + '注册App。\n\n验证码为：' + code + '\n（验证码有效期为5分钟）\n\n如非本人操作请忽略。'

    if not _sendEmail(data['email'], emailMsg):
        return _jsonToStr(code=400, data="验证码发送失败")
    return _jsonToStr(code=200, data="验证码发送成功")


# 设备列表
def devices_list_():
    if request.headers.get("UserToken") is None:
        return _jsonToStr(code=400, data="确实必要参数")
    token = request.headers['UserToken']
    id = _checkToken(token)
    if id == -1:
        return _jsonToStr(code=400, data="登录已过期")

    devices = []
    for i in id.devices.all():
        info = {}
        info['id'] = i.id
        info['name'] = i.name
        info['devicesId'] = i.devicesId
        info['devicesType'] = i.devicesType
        info['picUrl'] = i.picUrl
        devices.append(info)
    return _jsonToStr(code=200, data=devices)


# 添加设备
def devices_add_():
    if request.headers.get("UserToken") is None:
        return _jsonToStr(code=400, data="确实必要参数")
    token = request.headers['UserToken']
    id = _checkToken(token)
    if id == -1:
        return _jsonToStr(code=400, data="登录已过期")
    data = request.json

    if len(data['addDevices']) == 0:
        return _jsonToStr(code=400, data="设备列表为空")

    devicesList = []
    for item in data['addDevices']:
        devicesList.append(
            dataBase.Devices(name=item['name'],
                             devicesId=item['id'],
                             devicesType=item['type'],
                             picUrl=item['pic'],
                             userId=id.id
                             )
        )

    db.session.add_all(devicesList)
    db.session.commit()

    return _jsonToStr(data="添加成功")


if __name__ == '__main__':

    # 子查父
    de = dataBase.Devices.query.filter_by(id=1).first()
    print(de.user.user)

    # 夫查子
    user = dataBase.User.query.filter_by(id=1).first()
    print(user.devices.all())
