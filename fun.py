import hashlib
import re
from threading import Thread

from config import request, db, dbr, Message, mail, app
import dataBase
import json
import time
from datetime import datetime
import random


def _getTime():
    return time.strftime("%H:%M:%S", time.localtime())


def _getTimeDate():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def _getTimeDate_():
    current_datetime = datetime.now()
    return current_datetime.replace(microsecond=0);


def _getDate():
    return time.strftime("%Y-%m-%d", time.localtime())


def _getTimeInt():
    return time.time()


def _jsonToStr(code=200, msg="succeed", data=None):
    info = {'code': code, 'msg': msg, 'data': data, 'beFrom': 'Ks',
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
    userId = dataBase.User.query.filter_by(user=user.decode(), delTime=None).first()
    if userId is None:
        return -1
    return userId


# 登录
def login_():
    data = request.json
    print(data)

    if 'user' not in data.keys() or 'pwd' not in data.keys():
        return _jsonToStr(code=400, msg="缺少参数")

    if '' in data.values() or '' in data.values():
        return _jsonToStr(code=400, msg="参数不能为空")

    md5Pwd = _getMd5(data['user'] + "-/-" + data['pwd'])

    users = dataBase.User.query.filter(dataBase.User.user == data['user'],
                                       dataBase.User.passwd == md5Pwd, dataBase.User.delTime == None).first()

    if users is None:
        return _jsonToStr(code=400, msg="用户不存在或密码错误")
    resData = {}
    devices = []
    for i in users.devices.filter(dataBase.Devices.delTime == None).all():
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
        return _jsonToStr(code=400, msg="缺少参数")
    if '' in data.values() or '' in data.values():
        return _jsonToStr(code=400, msg="参数不能为空")

    verifyCode = dbr.get(data['user'] + "***" + data['email'])
    if verifyCode is None:
        return _jsonToStr(code=400, msg="验证码已过期，验证码错误")

    if verifyCode == data['code']:
        return _jsonToStr(code=400, msg="验证码已过期，验证码错误")
    try:
        md5Pwd = _getMd5(data['user'] + "-/-" + data['pwd'])
        db.session.add(dataBase.User(user=data['user'], passwd=md5Pwd, email=data['email'], createTime=_getTimeDate_()))
        db.session.commit()
        dbr.delete(data['code'])
        token = _generateToken(data['user'], data['pwd'])
        return _jsonToStr(data={"token": token})
    except Exception as e:
        print(e)
        return _jsonToStr(code=400, msg="注册失败")


# 注册验证码
def register_verifyCode_():
    try:
        data = request.json
        if 'user' not in data.keys() or 'email' not in data.keys():
            return _jsonToStr(code=400, msg="缺少参数")

        if '' in data.values() or '' in data.values():
            return _jsonToStr(code=400, msg="参数不能为空")

        if not _validateEmail(data['email']):
            return _jsonToStr(code=400, msg="邮箱格式错误")

        if dbr.get(data['email']) is not None:
            return _jsonToStr(code=400, msg="请求频繁，稍后再试")

        if dataBase.User.query.filter_by(user=data['user']).count() != 0 or \
                dataBase.User.query.filter_by(email=data['email']).count() != 0:
            return _jsonToStr(code=400, msg="账号或邮箱已被注册过")
        code = _randomCode()

        dbr.set(data['user'] + "***" + data['email'], code, ex=300)
        emailMsg = '你正在使用邮箱：' + data['email'] + '注册App。\n\n验证码为：' + code + '\n（验证码有效期为5分钟）\n\n如非本人操作请忽略。'

        if not _sendEmail(data['email'], emailMsg):
            return _jsonToStr(code=400, msg="验证码发送失败")
        # 同一个邮箱2分钟请求一次
        dbr.set(data['email'], "-", ex=120)
        return _jsonToStr(code=200, msg="验证码发送成功", data={})
    except Exception as e:
        print(e)
        return _jsonToStr(code=400, msg="未知")


# 设备列表
def devices_list_():
    if request.headers.get("UserToken") is None:
        return _jsonToStr(code=400, msg="缺少必要参数")
    token = request.headers['UserToken']
    id = _checkToken(token)
    if id == -1:
        return _jsonToStr(code=405, msg="登录已过期")

    devices = []
    for i in id.devices.filter(dataBase.Devices.delTime == None).all():
        info = {}
        info['id'] = i.id
        info['name'] = i.name
        info['devicesId'] = i.devicesId
        info['devicesType'] = i.devicesType
        info['picUrl'] = i.picUrl
        devices.append(info)
    print(_jsonToStr(code=200, data={"devices": devices}))
    return _jsonToStr(code=200, data={"devices": devices})


# 获取某类型的一添加的所有设备列表
def devices_type_list_(type):
    if request.headers.get("UserToken") is None or type == "":
        return _jsonToStr(code=400, msg="缺少必要参数")
    token = request.headers['UserToken']
    id = _checkToken(token)
    if id == -1:
        return _jsonToStr(code=405, msg="登录已过期")

    devices_ = dataBase.Devices.query.filter_by(devicesType=type).all()
    devices = []
    for i in devices_:
        devices.append(i.devicesId)
    return _jsonToStr(code=200, data=devices)


# 添加设备
def devices_add_():
    if request.headers.get("UserToken") is None:
        return _jsonToStr(code=400, msg="缺少必要参数")
    token = request.headers['UserToken']
    id = _checkToken(token)
    if id == -1:
        return _jsonToStr(code=405, msg="登录已过期")
    data = request.json

    if len(data['addDevices']) == 0:
        return _jsonToStr(code=400, msg="设备列表为空")

    if dataBase.Devices.query.filter(dataBase.Devices.devicesId == data['addDevices']['id'],
                                     dataBase.Devices.delTime == None).count() != 0:
        return _jsonToStr(code=401, msg="设备已被绑定过")

    devices = dataBase.Devices(name=data['addDevices']['name'],
                               devicesId=data['addDevices']['id'],
                               devicesType=data['addDevices']['type'],
                               picUrl=data['addDevices']['pic'],
                               userId=id.id,
                               createTime=_getTimeDate_())

    # devicesList = []
    # for item in data['addDevices']:
    #     devicesList.append(
    #         dataBase.Devices(name=item['name'],
    #                          devicesId=item['id'],
    #                          devicesType=item['type'],
    #                          picUrl=item['pic'],
    #                          userId=id.id,
    #                          createTime=_getTimeDate_())
    #     )

    db.session.add(devices)
    db.session.commit()

    return _jsonToStr(msg="添加成功")


# 获取设备类型列表
def get_devices_type_list_():
    if request.headers.get("UserToken") is None:
        return _jsonToStr(code=400, msg="缺少必要参数")
    token = request.headers['UserToken']
    id = _checkToken(token)
    if id == -1:
        return _jsonToStr(code=405, msg="登录已过期")
    devicesType = []
    devices_ = dataBase.DevicesType.query.filter(dataBase.DevicesType.delTime == None).all()
    for item in devices_:
        info = {}
        info['id'] = item.id
        info['name'] = item.name
        info['type'] = item.type
        info['picUrl'] = item.picUrl
        info['size'] = item.size
        info['createTime'] = str(item.createTime)
        devicesType.append(info)
    return _jsonToStr(code=200, data={"devicesType": devicesType})


# 添加设备类型
def devices_type_add_():
    if request.headers.get("UserToken") is None:
        return _jsonToStr(code=400, msg="缺少必要参数")
    token = request.headers['UserToken']
    id = _checkToken(token)
    if id == -1:
        return _jsonToStr(code=405, msg="登录已过期")
    data = request.json

    if id.role.value != 0:
        return _jsonToStr(code=400, msg="无权限")

    if len(data['addDevicesType']) == 0:
        return _jsonToStr(code=400, msg="设备列表为空")
    dataT = data['addDevicesType']
    dataDT = dataBase.DevicesType(name=dataT['name'],
                                  type=dataT['type'],
                                  picUrl=dataT['picUrl'],
                                  size=dataT['size'],
                                  createTime=_getTimeDate_())
    db.session.add(dataDT)
    return _jsonToStr(data="添加成功")


# 修改设备名称
def devices_edit_name_():
    if request.headers.get("UserToken") is None:
        return _jsonToStr(code=400, msg="缺少必要参数")
    token = request.headers['UserToken']
    ids = _checkToken(token)
    if ids == -1:
        return _jsonToStr(code=405, msg="登录已过期")
    data = request.json

    if data.get("name") is None or data.get("id") is None:
        return _jsonToStr(code=400, msg="缺少必要参数")

    editIs = ids.devices.filter(dataBase.Devices.id == int(data.get("id")),
                                dataBase.Devices.delTime == None).update({"name": data.get("name")})
    db.session.commit()

    return _jsonToStr(data="修改成功" if editIs == 1 else "修改失败")


# 设备校验
def devices_authentication_():
    result = {"result": "deny", "is_superuser": False}
    data = request.json

    if data['clientid'] == "services":
        result["result"] = "allow"
        result["is_superuser"] = True
        return json.dumps(result), 200, {"Content-Type": "application/json"}

    print(data)
    if 'user' not in data.keys() or 'pwd' not in data.keys() or "clientid" not in data.keys():
        return json.dumps(result), 404, {"Content-Type": "application/json"}

    if '' in data.values() or '' in data.values():
        return json.dumps(result), 404, {"Content-Type": "application/json"}

    md5Pwd = _getMd5(data['user'] + "-/-" + data['pwd'])

    users = dataBase.User.query.filter(dataBase.User.user == data['user'],
                                       dataBase.User.passwd == md5Pwd).first()

    if users is None:
        return json.dumps(result), 404, {"Content-Type": "application/json"}

    clientId = data['clientid']
    if clientId[len(clientId) - 3:] == "app":
        result["result"] = "allow"
        return json.dumps(result), 200, {"Content-Type": "application/json"}


    devices = users.devices.filter(dataBase.Devices.devicesId == data['clientid'],
                                   dataBase.Devices.delTime == None).first()

    if devices is None:
        return json.dumps(result), 404, {"Content-Type": "application/json"}

    state = dataBase.DevicesHistoryState(date=_getTimeDate(), state=True, devicesId=devices.id)
    db.session.add(state)
    db.session.commit()

    result["result"] = "allow"
    # print("devices:", result)
    return json.dumps(result), 200, {"Content-Type": "application/json"}


if __name__ == '__main__':
    pass
    # 子查父
    # de = dataBase.Devices.query.filter_by(id=1).first()
    # print(de.user.user)
    #

    user = dataBase.User.query.filter_by(id=1).first()

    print(user.devices.all())

    # # 夫查子
    # user = dataBase.User.query.filter_by(id=1).first()
    # print(user.devices.filter(dataBase.Devices.id == 2,dataBase.Devices.delTime != None).update({"name": "二坤1"}))
    # db.session.commit()

    #
    # devices_ = dataBase.Devices.query.all()
    # print(devices_)
    #
    # print(dataBase.User.query.filter_by(email="841369846@qq.com").count())

    # devices_ = dataBase.DevicesType.query.filter(dataBase.DevicesType.delTime == None).all()
    # print(devices_)
    #
    # print(_getTimeDate_())
    # userId = dataBase.User.query.filter_by(user="841369846", delTime=None).first()
    # print(userId.devices.filter(dataBase.Devices.delTime == None).all()[0].devicesId)
    # a = dataBase.Devices.query.filter(dataBase.Devices.devicesId == "203d74f95560",
    #                                   dataBase.Devices.delTime == None).all()
    #
    # print(a)
