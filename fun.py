import hashlib
import os.path
import re
from threading import Thread

import flask

from config import request, db, dbr, Message, mail, app, mqtt_client, mq
import dataBase
import json
import time
from datetime import datetime
import random
import base64
import numpy as np
import cv2
# import magic

# 生成设备状态下发话题
from picTobase64 import PicAndBase64


def time_to_seconds(days, hours, minutes, seconds):
    '''
    时间转秒
    :param days: 天
    :param hours: 时
    :param minutes: 分
    :param seconds: 秒
    :return:
    '''
    total_seconds = (days * 24 * 60 * 60) + (hours * 60 * 60) + (minutes * 60) + seconds
    return total_seconds


def seconds_to_time(seconds):
    '''
    秒转天、时、分、秒
    :param seconds: 秒
    :return:
    '''

    # 计算天数
    days = seconds // (24 * 60 * 60)

    # 计算剩余秒数
    remaining_seconds = seconds % (24 * 60 * 60)

    # 计算小时
    hours = remaining_seconds // (60 * 60)

    # 计算剩余秒数
    remaining_seconds %= (60 * 60)

    # 计算分钟
    minutes = remaining_seconds // 60

    # 计算剩余秒数
    seconds = remaining_seconds % 60

    return days, hours, minutes, seconds


def dis_day(seconds):
    '''
    不满足一天的计算
    :param seconds: 秒
    :return:
    '''
    return seconds % (24 * 60 * 60)


def devicesStateIssueTopic(userId: str) -> str:
    return "ks/server/general/" + userId + "/devices/state"


# 生成设备动作下发话题，服务端发送给设备的话题 （设备id）
def devicesIssueTopic(devicesId: str) -> str:
    return "ks/server/subordinate/" + devicesId + "/action"


def _getTime():
    return time.strftime("%H:%M:%S", time.localtime())


def _getTimeDate():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def _getTimeDate_():
    current_datetime = datetime.now()
    return current_datetime.replace(microsecond=0)


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


def rgb(r, g, b) -> bytes:
    return (((r & 0xf8) << 8) | ((g & 0xfc) << 3) | (b >> 3)).to_bytes(2, byteorder="big", signed=False)


# base64转cv2
def base64_to_cv2(base64_code):
    img_data = base64.b64decode(base64_code)
    img_array = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(img_array, cv2.COLOR_RGB2BGR)
    return img


# 邮箱格式判断
def _validateEmail(email):
    if re.match('^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$', email) != None:
        # if re.match('/^\w+@[a-z0-9]+\.[a-z]{2,4}$/', email) != None:
        return True
    else:
        return False


def _rgb(g, b, r):
    return ((r & 0xf8) << 8) | ((g & 0xfc) << 3) | ((b & 0xf8) >> 3)


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
    tok = dbr.get(user)
    if tok is not None:
        a = dbr.delete(tok)
        print(tok,a)
    token = _getMd5(user + '-' + pwd + str(_getTimeInt()))
    dbr.set(token, user)
    dbr.set(user, token)
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
    userId = dataBase.User.query.filter_by(account=user.decode(), delTime=None).first()
    if userId is None:
        return -1
    return userId


# 登录
def login_():
    data = request.json
    if 'user' not in data.keys() or 'pwd' not in data.keys():
        return _jsonToStr(code=400, msg="缺少参数")

    if '' in data.values() or '' in data.values():
        return _jsonToStr(code=400, msg="参数不能为空")

    md5Pwd = _getMd5(data['pwd'] + "-/- whose")


    users = dataBase.User.query.filter((dataBase.User.account == data['user']) | (dataBase.User.email == data['user']),
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
    resData['token'] = _generateToken(users.account, data['pwd'])

    return _jsonToStr(data=resData)


# 注册
def register_():
    def createAccount():
        alist = [0] * 10
        for i in range(len(alist)):
            alist[i] = random.randint(10021, 99999)
        acc = random.sample(alist,1)[0]
        if dataBase.User.query.filter(dataBase.User.account == str(acc)).count() == 0:
            return str(acc)
        return createAccount()

    data = request.json
    if 'email' not in data.keys() or 'code' not in data.keys() or 'pwd' not in data.keys():
        return _jsonToStr(code=400, msg="缺少参数")
    if '' in data.values() or '' in data.values():
        return _jsonToStr(code=400, msg="参数不能为空")

    verifyCode = dbr.get("verifyCode"+"-->" + data['email'])
    if verifyCode is None:
        return _jsonToStr(code=400, msg="验证码已过期，验证码错误")

    if verifyCode == data['code']:
        return _jsonToStr(code=400, msg="验证码已过期，验证码错误")
    try:
        md5Pwd = _getMd5(data['pwd'] + "-/- whose")
        acc = createAccount()
        db.session.add(
            dataBase.User(account=acc, userId=_getMd5(acc), passwd=md5Pwd, email=data['email'],
                          createTime=_getTimeDate_()))
        db.session.commit()
        dbr.delete("verifyCode"+"-->" + data['email'])
        dbr.delete(data['email'])
        token = _generateToken(acc, data['pwd'])
        return _jsonToStr(data={"token": token})
    except Exception as e:
        print(e)
        return _jsonToStr(code=400, msg="注册失败")


# 注册验证码
def register_verifyCode_():
    try:
        data = request.json
        if 'email' not in data.keys():
            return _jsonToStr(code=400, msg="缺少参数")

        if '' in data.values() or '' in data.values():
            return _jsonToStr(code=400, msg="参数不能为空")

        if not _validateEmail(data['email']):
            return _jsonToStr(code=400, msg="邮箱格式错误")

        if dbr.get(data['email']) is not None:
            return _jsonToStr(code=400, msg="请求频繁，稍后再试")

        if dataBase.User.query.filter_by(email=data['email']).count() != 0:
            return _jsonToStr(code=400, msg="邮箱已被注册过")
        code = _randomCode()

        dbr.set("verifyCode"+"-->" + data['email'], code, ex=300)
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
    ids = _checkToken(token)
    if ids == -1:
        return _jsonToStr(code=405, msg="登录已过期")

    devices = []
    for i in ids.devices.filter(dataBase.Devices.delTime == None).all():
        info = {}
        info['id'] = i.id
        info['name'] = i.name
        info['devicesId'] = i.devicesId
        info['devicesType'] = i.devicesType
        info['picUrl'] = i.picUrl
        devices.append(info)
    return _jsonToStr(code=200, data={"devices": devices})


# 获取某类型的一添加的所有设备列表
# def devices_type_list_(type):
#     if request.headers.get("UserToken") is None or type == "":
#         return _jsonToStr(code=400, msg="缺少必要参数")
#     token = request.headers['UserToken']
#     ids = _checkToken(token)
#     if ids == -1:
#         return _jsonToStr(code=405, msg="登录已过期")
#
#     devices_ = dataBase.Devices.query.filter_by(devicesType=type).all()
#     devices = []
#     for i in devices_:
#         devices.append(i.devicesId)
#     return _jsonToStr(code=200, data=devices)


# 添加设备
def devices_add_():
    if request.headers.get("UserToken") is None:
        return _jsonToStr(code=400, msg="缺少必要参数")
    token = request.headers['UserToken']
    ids = _checkToken(token)
    if ids == -1:
        return _jsonToStr(code=405, msg="登录已过期")
    data = request.json

    if len(data['addDevices']) == 0:
        return _jsonToStr(code=400, msg="设备列表为空")

    if dataBase.Devices.query.filter(dataBase.Devices.devicesId == data['addDevices']['id'],
                                     dataBase.Devices.delTime == None).count() != 0:
        return _jsonToStr(code=401, msg="设备已被绑定过")
    type = dataBase.DevicesType.query.filter(dataBase.DevicesType.id == data['addDevices']['type']).first()

    if type is None:
        return _jsonToStr(code=400, msg="没有该设备类型")

    devices = dataBase.Devices(name=data['addDevices']['name'],
                               devicesId=data['addDevices']['id'],
                               devicesType=data['addDevices']['type'],
                               picUrl=data['addDevices']['pic'],
                               userId=ids.id,
                               createTime=_getTimeDate_())
    db.session.add(devices)
    db.session.commit()
    if type.type == dataBase.ConfigType.PROGRAM:
        did = dataBase.Devices.query.filter(dataBase.Devices.devicesId == data['addDevices']['id'],
                                            dataBase.Devices.delTime == None).first()

        nowGpio = dataBase.Gpio(devicesId=did.id,
                                io=type.gpio,
                                name=data['addDevices']['name'],
                                type=dataBase.ConfigType.PROGRAM,
                                createTime=_getTimeDate_())
        db.session.add(nowGpio)
        db.session.commit()

    return _jsonToStr(msg="添加成功")


# 添加设备GPIO引脚
def devices_gpio_add_():
    try:
        print(request.json)
        if request.headers.get("UserToken") is None:
            return _jsonToStr(code=400, msg="缺少必要参数")
        token = request.headers['UserToken']
        ids = _checkToken(token)
        print(ids)
        if ids == -1:
            return _jsonToStr(code=405, msg="登录已过期")
        data = request.json
        print(data)
        devices = ids.devices.filter(dataBase.Devices.id == data['devicesId'],
                                     dataBase.Devices.delTime == None).first()
        if devices is None:
            return _jsonToStr(code=400, msg="设备不存在")

        if devices.gpio.filter(dataBase.Gpio.io == data["io"], dataBase.Gpio.delTime == None).first() is not None:
            return _jsonToStr(code=400, msg="子设备已存在")

        nowGpio = dataBase.Gpio(devicesId=devices.id,
                                io=data['io'],
                                name=data['name'],
                                icon=data['icon'],
                                type=dataBase.ConfigType.SWITCH if data['type'] == 0 else dataBase.ConfigType.PROGRAM,
                                createTime=_getTimeDate_())
        db.session.add(nowGpio)
        db.session.commit()
        return _jsonToStr(msg="添加成功")
    except Exception as a:
        print(a)
        return a


# 添加设备Gpio引脚的任务
def devices_gpio_task_add_():
    def create_task_id(devicesId, id):
        taskId = str(devicesId) + "-" + str(id) + "-" + str(_randomCode(6))
        if dataBase.SwitchGpio.query.filter(dataBase.SwitchGpio.taskId == taskId).count() == 0:
            return taskId
        return create_task_id(devicesId, id)

    if request.headers.get("UserToken") is None:
        return _jsonToStr(code=400, msg="缺少必要参数")
    token = request.headers['UserToken']
    ids = _checkToken(token)
    if ids == -1:
        return _jsonToStr(code=405, msg="登录已过期")
    data = request.json
    gpio = dataBase.Gpio.query.filter(
        dataBase.Gpio.id == data.get("gpio"), dataBase.Gpio.delTime == None).first()

    if gpio is None:
        return _jsonToStr(code=400, msg="子设备不存在")

    if data.get("value") == 0:
        value = dataBase.SwitchValue.OPEN
    elif data.get("value") == 1:
        value = dataBase.SwitchValue.CLOSE
    elif data.get("value") == 2:
        value = dataBase.SwitchValue.FLICKER
    else:
        value = dataBase.SwitchValue.OPEN
    # taskId = create_task_id(gpio.devicesId, gpio.id)

    lasting = 2 if data.get("lasting") == 2 else 1

    # if data.get('startDate') > 0:

    taskStart = False if data.get("startDate") > 0 else True

    if not taskStart:
        m = data.get("startDate") - int(time.time())  # 未来时间减去当前时间

        if m < 86400:
            sectionCount = 0
            # delay = m
        else:
            # delay = 86400
            sectionCount = seconds_to_time(m)[0]
    else:
        sectionCount = seconds_to_time(data.get("interval"))[0] + 1
        # delay = dis_day(data.get("interval"))

    switchGpio = dataBase.SwitchGpio(gpioId=gpio.id,
                                     taskName=data.get("name"),
                                     value=value,
                                     interval=data.get("interval"),
                                     lasting=data.get("lasting"),
                                     startDate=data.get("startDate"),
                                     destroyDate=data.get("destroyDate"),
                                     taskStart=taskStart,
                                     sectionCount=sectionCount,
                                     finish=False,
                                     date=int(time.time()),
                                     createTime=_getTimeDate_())

    db.session.add(switchGpio)
    db.session.flush()
    # print(switchGpio.json())
    mq.send(switchGpio.json())


    db.session.commit()

    return _jsonToStr(msg="添加成功")


# 删除设备
def devices_del_():
    if request.headers.get("UserToken") is None:
        return _jsonToStr(code=400, msg="缺少必要参数")
    token = request.headers['UserToken']
    ids = _checkToken(token)
    if ids == -1:
        return _jsonToStr(code=405, msg="登录已过期")
    data = request.json

    devices = ids.devices.filter(dataBase.Devices.delTime == None,
                                 dataBase.Devices.devicesId == data.get("devicesId")).first()

    # devices = dataBase.Devices.query.filter(dataBase.Devices.devicesId == "",dataBase.Devices.delTime == None).first()
    # 设备下的gpio
    for i in devices.gpio.filter(dataBase.Gpio.delTime == None).all():
        # gpio下的任务
        for j in i.switch.filter(dataBase.SwitchGpio.delTime == None).all():
            # scheduler.remove_job(j.taskId)
            j.delTime = _getTimeDate_()
        i.delTime = _getTimeDate_()
    devices.delTime = _getTimeDate_()
    db.session.commit()
    return _jsonToStr(msg="删除成功")


# 获取设备类型列表
def get_devices_type_list_():
    if request.headers.get("UserToken") is None:
        return _jsonToStr(code=400, msg="缺少必要参数")
    token = request.headers['UserToken']
    ids = _checkToken(token)
    if ids == -1:
        return _jsonToStr(code=405, msg="登录已过期")
    devicesType = []
    devices_ = dataBase.DevicesType.query.filter(dataBase.DevicesType.delTime == None).all()
    for item in devices_:
        info = {}
        info['id'] = item.id
        info['name'] = item.name
        info['type'] = item.typeName
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
    ids = _checkToken(token)
    if ids == -1:
        return _jsonToStr(code=405, msg="登录已过期")
    data = request.json

    if ids.role.value != 0:
        return _jsonToStr(code=400, msg="无权限")

    if len(data['addDevicesType']) == 0:
        return _jsonToStr(code=400, msg="设备列表为空")
    dataT = data['addDevicesType']
    dataDT = dataBase.DevicesType(name=dataT['name'],
                                  typeName=dataT['typeName'],
                                  type=dataBase.ConfigType.SWITCH if dataT[
                                                                         'type'] == 0 else dataBase.ConfigType.PROGRAM,
                                  gpio=dataT['io'],
                                  picUrl=dataT['picUrl'],
                                  size=dataT['size'],
                                  createTime=_getTimeDate_())
    db.session.add(dataDT)
    db.session.commit()

    return _jsonToStr(data="添加成功")


# 设备详情
def devices_info_():
    if request.headers.get("UserToken") is None:
        return _jsonToStr(code=400, msg="缺少必要参数")
    token = request.headers['UserToken']
    ids = _checkToken(token)
    if ids == -1:
        return _jsonToStr(code=405, msg="登录已过期")
    data = request.json
    if data.get("id") is None:
        return _jsonToStr(code=400, msg="缺少必要参数")
    info = {"gpio": []}
    devices = ids.devices.filter(dataBase.Devices.id == int(data.get("id")),
                                 dataBase.Devices.delTime == None).first()
    if devices is None:
        return _jsonToStr(code=400, msg="设备不存在")
    devicesType = dataBase.DevicesType.query.filter(dataBase.DevicesType.id == devices.devicesType).first()

    gpio_list = []
    for gpio_ in devices.gpio.filter(dataBase.Gpio.delTime == None).all():
        gpio_d = {}
        gpio_d.update({"id": gpio_.id})
        gpio_d.update({"io": gpio_.io})
        gpio_d.update({"name": gpio_.name})
        gpio_d.update({"icon": gpio_.icon})
        gpio_d.update({"type": gpio_.type})
        s_list = []
        for s in gpio_.switch.filter(dataBase.SwitchGpio.delTime == None).all():
            s_d = {}
            s_d.update({"id": s.id})
            s_d.update({"taskId": s.taskId})
            s_d.update({"taskName": s.taskName})
            s_d.update({"value": s.value})
            s_d.update({"interval": s.interval})
            s_d.update({"lasting": s.lasting})
            s_d.update({"startDate": s.startDate})
            s_d.update({"destroyDate": s.destroyDate})
            s_d.update({"finish": s.finish})
            s_d.update({"interval": s.interval})
            s_list.append(s_d)

        gpio_d.update({"task": s_list})

        gpio_list.append(gpio_d)
    info['gpio'] = gpio_list
    info.update({"name": devices.name})
    info.update({"devicesId": devices.devicesId})
    info.update({"type": {"typeName": devicesType.typeName, "type": devicesType.type.value,
                          "picUrl": devicesType.picUrl, "size": devicesType.size}})

    # info.update({"type": {"typeName": devices.devicesType.typeName}})
    # info.update({"type": {"type": devices.devicesType.type}})
    # info.update({"type": {"picUrl": devices.devicesType.picUrl}})
    # info.update({"type": {"size": devices.devicesType.size}})

    return _jsonToStr(data=info)


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

    if 'user' not in data.keys() or 'pwd' not in data.keys() or "clientid" not in data.keys():
        return json.dumps(result), 404, {"Content-Type": "application/json"}

    if '' in data.values() or '' in data.values():
        return json.dumps(result), 404, {"Content-Type": "application/json"}
    md5Pwd = _getMd5(data['pwd'] + "-/- whose")
    users = dataBase.User.query.filter((dataBase.User.account == data['user']) | (dataBase.User.email == data['user']),
                                       dataBase.User.passwd == md5Pwd, dataBase.User.delTime == None).first()

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


# 上传Bin文件
def ota_bin_upload_():
    fields = ['type', 'versions', 'md5', 'explain', 'fileName', 'compel']
    if request.headers.get("UserToken") is None:
        return _jsonToStr(code=400, msg="缺少必要参数")
    token = request.headers['UserToken']
    ids = _checkToken(token)
    if ids == -1:
        return _jsonToStr(code=405, msg="登录已过期")
    data = request.form

    if ids.role.value != 0:
        return _jsonToStr(code=400, msg="无权限")

    if 'type' not in data.keys():
        return _jsonToStr(code=400, msg="缺少必要参数")

    binType = dataBase.DevicesType.query.filter(dataBase.DevicesType.typeName == data.get('type'),
                                                dataBase.DevicesType.delTime == None).first()
    bin = dataBase.OtaBin.query.filter(dataBase.OtaBin.type == binType.id, dataBase.OtaBin.delTime == None).all()

    if 'versions' not in data.keys():
        if len(bin) != 0:
            versions = bin[-1].versions + 1
        else:
            versions = 1.0
    else:
        versions = data.get("versions")

    file = request.files['file']
    if file.filename == '':
        return _jsonToStr(code=400, msg="未上传文件")
    md5_hash = hashlib.md5()
    md5_hash.update(file.stream.read())
    file_md5 = md5_hash.hexdigest()

    file.save(os.path.join(app.config['DEVICES_UPDATE_BIN_PATH'], file_md5 + '.bin'))

    now = dataBase.OtaBin(type=binType.id,
                          versions=versions,
                          md5=file_md5,
                          explain=data.get("explain") if 'explain' in data.keys() else None,
                          fileName=file_md5 + ".bin",
                          fileSize=file.content_length,
                          compel=data.get("compel") if 'compel' in data.keys() else dataBase.UpdateType.OFFICIAL.value,
                          createTime=_getTimeDate_())
    db.session.add(now)

    return _jsonToStr(data="上传成功")


def ota_info_get_(type):
    t = dataBase.DevicesType.query.filter(dataBase.DevicesType.typeName == type,
                                          dataBase.DevicesType.delTime == None).first()
    if t is None:
        return _jsonToStr(code=400, msg="无类型更新")
    ota = dataBase.OtaBin.query.filter_by(type=t.id, delTime=None).order_by(dataBase.OtaBin.versions.desc()).first()
    if ota is None:
        return _jsonToStr(code=400, msg="暂无更新")
    ret = {'versions': ota.versions, "md5": ota.md5, 'type': t.typeName, 'compel': ota.value, 'name': ota.fileName}

    return _jsonToStr(data=ret)


# ota下载，设备类型，文件名称，下载码
def download_ota_(otaType, fileName, code):
    verify = ['66535', '2023', '147', 'kun', 'osdf']

    if code not in verify or code is None or code == '':
        return _jsonToStr(code=400, msg="下载码错误")

    type = dataBase.DevicesType.query.filter(dataBase.DevicesType.typeName == otaType,
                                             dataBase.DevicesType.delTime == None).first()
    if type is None:
        return _jsonToStr(code=400, msg="无类型更新")

    ota = dataBase.OtaBin.query.filter(dataBase.OtaBin.type == type.id, dataBase.OtaBin.fileName == fileName,
                                       dataBase.OtaBin.delTime == None).first()
    if ota is None:
        return _jsonToStr(code=400, msg="无类型更新")

    ota.downloadNum += 1
    db.session.commit()
    return flask.send_from_directory(app.config.get('DEVICES_UPDATE_BIN_PATH'),
                                     ota.fileName + ".bin",
                                     as_attachment=True)
    # return flask.send_file(os.path.join(app.config.get('DEVICES_UPDATE_BIN_PATH'), ota.fileName + ".bin"),
    #                        as_attachment=True)


def switch_action(task):
    # taskId = kwargs['taskId']

    # task = dataBase.SwitchGpio.query.filter(dataBase.SwitchGpio.taskId == taskId,
    #                                         dataBase.SwitchGpio.delTime == None).first()

    print(task.value)
    if task is None:
        return
    if task.value == dataBase.SwitchValue.OPEN:
        pla = bytes([2, task.gpio.io, 0])
        mqtt_client.publish(devicesIssueTopic(task.gpio.devices.devicesId), pla)
        task.gpio.state = True
        db.session.commit()

    elif task.value == dataBase.SwitchValue.CLOSE:
        pla = bytes([2, task.gpio.io, 1])
        mqtt_client.publish(devicesIssueTopic(task.gpio.devices.devicesId), pla)
        task.gpio.state = False
        db.session.commit()

    elif task.value == dataBase.SwitchValue.FLICKER:
        state = 0 if task.gpio.state == False else 1
        pla = bytes([2, task.gpio.io, state])
        mqtt_client.publish(devicesIssueTopic(task.gpio.devices.devicesId), pla)
        task.gpio.state = True if state == 0 else False
        db.session.commit()


# 控制io口
def switch_ctrl_(jo, devices: dataBase.Devices):
    # io 为 gpio表的ID
    a = {"action": "switch", "data": {"io": 1, "value": 0}}

    gpio = devices.gpio.filter(dataBase.Gpio.id == jo.get("data").get("io"), dataBase.Gpio.delTime == None).first()
    if gpio is None or gpio.type != dataBase.ConfigType.SWITCH:
        return
    pla = bytes([2, gpio.io, jo.get("data").get("value")])
    gpio.state = True if jo.get("data").get("value") == 0 else False
    db.session.commit()
    mqtt_client.publish(devicesIssueTopic(devices.devicesId), pla)


# 下发修改wifi配置的消息
def wifi_edit_issue_(jo, devices: dataBase.Devices):
    a = {"action": "wifi", "restart": 0,
         "wifi": {"dhcp": 0, "ssid": "TP-LINK_803F", "pwd": "ks123456", "ip": [192, 168, 0, 159],
                  "maskCode": [255, 255, 255, 0], "gateway": [192, 168, 0, 254], "dns": [192, 168, 0, 254]}}

    wifi = json.dumps(jo.get("wifi"))
    wifiRestart = int(jo.get("restart"))
    pla = bytes([1, wifiRestart]) + bytes(wifi, "utf-8")
    mqtt_client.publish(devicesIssueTopic(devices.devicesId), pla)


# 控制单个像素
def matrix_pixel_(jo, devices: dataBase.Devices):
    a = {"action": "pixel", "data": {"x": 0, "y": 0, "color": [1, 1, 1]}}
    pla = bytes([4, jo.get("data").get("x"),
                 jo.get("data").get("y")]) + rgb(jo.get("data").get("color")[0],
                                                 jo.get("data").get("color")[1],
                                                 jo.get("data").get("color")[2])
    # pla = bytes([4, jo.get("data").get("x"), jo.get("data").get("y"),
    #              jo.get("data").get("color")[0], jo.get("data").get("color")[1], jo.get("data").get("color")[2]])
    mqtt_client.publish(devicesIssueTopic(devices.devicesId), pla)


# 清屏
def matrix_pixel_fill_(jo, devices: dataBase.Devices):
    pla = bytes([3]) + rgb(jo.get("data").get("color")[0],
                           jo.get("data").get("color")[1],
                           jo.get("data").get("color")[2])

    mqtt_client.publish(devicesIssueTopic(devices.devicesId), pla)


# 显示图片
def matrix_pixel_bmp_(jo, devices: dataBase.Devices):
    # data = [
    #     [[0, 1, 0], [255, 235, 59], [255, 235, 59], [255, 235, 59], [255, 235, 59], [255, 235, 59], [255, 235, 59],
    #      [0, 1, 0]],
    #     [[255, 235, 59], [255, 235, 59], [255, 235, 59], [255, 235, 59], [255, 235, 59], [255, 235, 59], [255, 235, 59],
    #      [255, 235, 59]],
    #     [[255, 235, 59], [0, 0, 0], [0, 0, 0], [255, 235, 59], [255, 235, 59], [0, 0, 0], [0, 0, 0], [255, 235, 59]],
    #     [[255, 235, 59], [255, 235, 59], [0, 0, 0], [255, 235, 59], [255, 235, 59], [255, 235, 59], [0, 0, 0],
    #      [255, 235, 59]],
    #     [[255, 235, 59], [255, 235, 59], [255, 235, 59], [255, 235, 59], [255, 235, 59], [255, 235, 59], [255, 235, 59],
    #      [255, 235, 59]],
    #     [[255, 235, 59], [255, 235, 59], [255, 235, 59], [0, 0, 0], [0, 0, 0], [0, 0, 0], [255, 235, 59],
    #      [255, 235, 59]],
    #     [[255, 235, 59], [255, 235, 59], [255, 235, 59], [255, 235, 59], [255, 235, 59], [255, 235, 59], [255, 235, 59],
    #      [255, 235, 59]],
    #     [[0, 1, 0], [255, 235, 59], [255, 235, 59], [255, 235, 59], [255, 235, 59], [255, 235, 59], [255, 235, 59],
    #      [0, 1, 0]]
    # ]
    #
    #
    # pla = bytes([5, 0, 0, 8, 8])
    #
    # for i in data:
    #     for j in i:
    #         pla = pla + rgb(j[0], j[1], j[2])
    #
    # mqtt_client.publish(devicesIssueTopic(devices.devicesId), pla)

    a = {"action": "pixel-bmp", "data": {"base64": ""}}
    pla = bytes([5, 0, 0]) + PicAndBase64(jo.get("data").get("base64")).getBase64Pixel()
    mqtt_client.publish(devicesIssueTopic(devices.devicesId), pla)


if __name__ == '__main__':
    # 子查父
    # de = dataBase.Devices.query.filter_by(id=1).first()
    # print(de.user.user)
    #

    # user = dataBase.User.query.filter_by(id=1).first()
    #
    # dataBase.Devices.query.filter(dataBase.Devices.devicesId == "1-9").update({"delTime": "2023-07-12 23:52:19"},
    #                                                                           synchronize_session=False)
    # db.session.commit()
    #
    # print(user.devices.first().devicesId)

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
    # ids = _checkToken("b739d352776579b3f75245069b058a53")
    # de = ids.devices.filter(dataBase.Devices.id == 1).first()
    # print(de)
    # gp = de.gpio.filter(dataBase.Gpio.io == 1).first()
    # print(gp)
    # type = dataBase.DevicesType.query.filter(dataBase.DevicesType.id == 1).first()
    # print(type.type.value)
    # devices_ = dataBase.Devices.query.filter(dataBase.Devices.id == 1).first()
    # print(devices_.user.user)
    #
    # task = dataBase.SwitchGpio.query.filter(dataBase.SwitchGpio.taskId == "2-1-287529",
    #                                         dataBase.SwitchGpio.delTime == None).first()
    # print(task.gpio.devices.devicesId)
    user = dataBase.User.query.filter(dataBase.User.user == "841369846", dataBase.User.delTime == None).first()
    devices = user.devices.filter(dataBase.Devices.id == 11,
                                  dataBase.Devices.delTime == None).first()
    info = {"gpio": []}
    devicesType = dataBase.DevicesType.query.filter(dataBase.DevicesType.id == devices.devicesType).first()
    gpio_list = []
    for gpio_ in devices.gpio.filter(dataBase.Gpio.delTime == None).all():
        gpio_d = {}
        gpio_d.update({"id": gpio_.id})
        gpio_d.update({"io": gpio_.io})
        gpio_d.update({"name": gpio_.name})
        gpio_d.update({"icon": gpio_.icon})
        gpio_d.update({"type": gpio_.type.value})
        s_list = []
        for s in gpio_.switch.filter(dataBase.SwitchGpio.delTime == None).all():
            s_d = {}
            s_d.update({"id": s.id})
            s_d.update({"taskId": s.taskId})
            s_d.update({"taskName": s.taskName})
            s_d.update({"value": s.value.value})
            s_d.update({"interval": json.loads(s.interval)})
            s_d.update({"lasting": s.lasting})
            s_d.update({"startDate": s.startDate})
            s_d.update({"destroyDate": s.destroyDate})
            s_d.update({"finish": s.finish})
            s_list.append(s_d)

        gpio_d.update({"task": s_list})

        gpio_list.append(gpio_d)
    info.update({"name": devices.name})
    info.update({"devicesId": devices.devicesId})
    info['gpio'] = gpio_list

    info.update({"type": {"typeName": devicesType.typeName, "type": devicesType.type.value,
                          "picUrl": devicesType.picUrl, "size": devicesType.size}})
    # info.update({"type": {}})
    # info.update({"type": {"picUrl": devicesType.picUrl}})
    # info.update({"type": {"size": devicesType.size}})

    print(info)

    # devices_d = user.devices.filter(dataBase.Devices.delTime == None,
    #                                 dataBase.Devices.devicesId == "pc-test").first()
    # print(devices_d.gpio.filter(dataBase.Gpio.delTime == None).all()[0].switch.all()[0].taskId)
