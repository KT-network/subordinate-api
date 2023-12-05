import json
import time

from config import app, db, mqtt_client, mq
import fun
import dataBase
import logging


def mq_call(ch, method, properties, body):
    data = json.loads(body)
    newData = data.copy()
    print(fun._getTimeDate())
    with app.app_context():
        base = dataBase.SwitchGpio.query.filter(dataBase.SwitchGpio.id == data.get("id"),
                                                dataBase.SwitchGpio.delTime == None).first()
        print(1)
        if base is None:
            print("base不存在")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        print(2)
        if base.finish:
            # 任务执行结束
            print("任务执行结束")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        print(3)
        if base.destroyDate != -1 and base.destroyDate - int(time.time()) < 0:
            print("执行时间结束")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            base.finish = True
            db.session.commit()
            return
        print(4)

        if base.lasting == 1:
            print(5)
            # 持久任务
            if base.taskStart:
                print(6)
                # 任务以开始执行
                if base.sectionCount > 1:
                    print(7)
                    delay = 86400
                    base.sectionCount -= 1
                    newData['sectionCount'] = base.sectionCount
                    mq.send(json.dumps(newData), delay)
                elif base.sectionCount == 1:
                    print(8)
                    # 不满足一天的时间
                    delay = fun.dis_day(base.interval)
                    base.sectionCount -= 1
                    newData['sectionCount'] = base.sectionCount
                    mq.send(json.dumps(newData), delay)
                else:
                    print(9)
                    # 执行任务
                    day = fun.seconds_to_time(base.interval)[0] + 1
                    base.sectionCount = day
                    newData['sectionCount'] = day
                    fun.switch_action(base)
                    mq.send(json.dumps(newData))
                db.session.commit()
            else:
                # 任务还在等待开始阶段
                if base.sectionCount > 1:
                    delay = 86400
                    base.sectionCount -= 1
                    newData['sectionCount'] = base.sectionCount
                    mq.send(json.dumps(newData), delay)
                elif base.sectionCount == 1:
                    # 不足一天
                    t = base.startDate - base.date
                    if t < 0:
                        t = 0
                    delay = fun.dis_day(t)
                    base.sectionCount -= 1
                    newData['sectionCount'] = base.sectionCount
                    mq.send(json.dumps(newData), delay)
                else:
                    # 计数等0
                    # 修改参数
                    base.taskStart = True
                    base.sectionCount = fun.seconds_to_time(base.interval)[0] + 1
                    newData['sectionCount'] = base.sectionCount
                    newData['taskStart'] = base.taskStart
                    mq.send(json.dumps(newData))
                db.session.commit()

        elif base.lasting == 2:
            if base.startDate < 0:
                # 立即执行
                base.taskStart = True
                base.finish = True
                fun.switch_action(base)
            else:
                # 有开始时间
                if base.sectionCount > 1:
                    delay = 86400
                    base.sectionCount -= 1
                    newData['sectionCount'] = base.sectionCount
                    mq.send(json.dumps(newData), delay)
                elif base.sectionCount == 1:
                    t = base.startDate - base.date
                    if t < 0:
                        t = 0
                    delay = fun.dis_day(t)
                    base.sectionCount -= 1
                    newData['sectionCount'] = base.sectionCount
                    mq.send(json.dumps(newData), delay)
                else:
                    base.taskStart = True
                    base.finish = True
                    fun.switch_action(base)
            db.session.commit()

        ch.basic_ack(delivery_tag=method.delivery_tag)



@mqtt_client.on_connect()
def connect(a,b,c,d):
    print(d)

@mqtt_client.on_message()
def handle_message(client, userdata, msg):
    topics = msg.topic.split("/")
    print(topics)

    with app.app_context():
        if topics[len(topics) - 1] == "connected":
            jo = json.loads(msg.payload)
            userName = jo.get("username")
            userId = fun._getMd5(userName)
            if jo.get("clientid")[- 3:] == "app":
                if jo.get("clientid")[:-4] == userId:

                    dataBase.User.query.filter(
                        (dataBase.User.account == userName) | (dataBase.User.email == userName),
                        dataBase.User.delTime == None).update(
                        {"state": True})
                    db.session.commit()

                    devices = dataBase.User.query.filter(
                        (dataBase.User.account == userName) | (dataBase.User.email == userName),
                        dataBase.User.delTime == None).first().devices.filter(
                        dataBase.Devices.delTime == None).all()
                    devicesState = {}
                    for item in devices:
                        devicesState.update({item.devicesId: item.state})
                    mqtt_client.publish(fun.devicesStateIssueTopic(userId), json.dumps(devicesState))
            else:
                user = dataBase.User.query.filter(
                    (dataBase.User.account == userName) | (dataBase.User.email == userName),
                    dataBase.User.delTime == None).first()
                if user is not None:
                    user.devices.filter(dataBase.Devices.delTime == None,
                                        dataBase.Devices.devicesId == jo.get("clientid")).update(
                        {"state": True})
                    db.session.commit()
                    devices_d = user.devices.filter(dataBase.Devices.delTime == None,
                                                    dataBase.Devices.devicesId == jo.get("clientid")).first()
                    for i in devices_d.gpio.filter(dataBase.Gpio.delTime == None).all():
                        print(i)
                        for j in i.switch.filter(dataBase.SwitchGpio.delTime == None).all():
                            # scheduler.resume_job(j.taskId)
                            print("上线")
                            print(j.taskId)
                    if user.state:
                        devices = user.devices.filter(dataBase.Devices.delTime == None).all()
                        devicesState = {}
                        for item in devices:
                            devicesState.update({item.devicesId: item.state})
                        mqtt_client.publish(fun.devicesStateIssueTopic(userId), json.dumps(devicesState))
                        # mqtt_client.subscribe(fun.appSubscribeTopic(userId, jo.get("clientid")))

        elif topics[len(topics) - 1] == "disconnected":
            jo = json.loads(msg.payload)
            userName = jo.get("username")
            userId = fun._getMd5(userName)
            if jo.get("clientid")[- 3:] == "app":
                if jo.get("clientid")[:-4] == userId:
                    dataBase.User.query.filter(
                        (dataBase.User.account == userName) | (dataBase.User.email == userName),
                        dataBase.User.delTime == None).update(
                        {"state": False})
                    db.session.commit()
            else:
                user = dataBase.User.query.filter(
                    (dataBase.User.account == userName) | (dataBase.User.email == userName),
                    dataBase.User.delTime == None).first()
                if user is not None:
                    user.devices.filter(dataBase.Devices.delTime == None,
                                        dataBase.Devices.devicesId == jo.get("clientid")).update(
                        {"state": False})
                    db.session.commit()

                    devices_d = user.devices.filter(dataBase.Devices.delTime == None,
                                                    dataBase.Devices.devicesId == jo.get("clientid")).first()
                    for i in devices_d.gpio.filter(dataBase.Gpio.delTime == None).all():
                        for j in i.switch.filter(dataBase.SwitchGpio.delTime == None).all():
                            # scheduler.pause_job(j.taskId)
                            print("掉线")
                            print(j.taskId)

                    if user.state:
                        devices = user.devices.filter(dataBase.Devices.delTime == None).all()
                        devicesState = {}
                        for item in devices:
                            devicesState.update({item.devicesId: item.state})
                        mqtt_client.publish(fun.devicesStateIssueTopic(userId), json.dumps(devicesState))
                        # mqtt_client.unsubscribe(fun.appSubscribeTopic(userId, jo.get("clientid")))

        elif topics[len(topics) - 1] == "action" and topics[1] == "general":
            devicesId = topics[len(topics) - 2]
            generalId = topics[len(topics) - 3]
            try:
                jo = json.loads(msg.payload)
            except:
                return
            devices = dataBase.User.query.filter(
                dataBase.User.userId == generalId, dataBase.User.delTime == None
            ).first().devices.filter(
                dataBase.Devices.devicesId == devicesId, dataBase.Devices.delTime == None
            ).first()

            if devices is None:
                return

            if jo.get("action") == "switch":
                '''io 引脚控制'''
                fun.switch_ctrl_(jo, devices)
            elif jo.get("action") == "wifi":
                '''配置wifi'''
                fun.wifi_edit_issue_(jo, devices)
            elif jo.get("action") == "pixel":
                '''控制单个像素(每个设备只有一个pixel引脚)'''
                fun.matrix_pixel_(jo, devices)
            elif jo.get("action") == "pixel-fill":
                '''清屏'''
                fun.matrix_pixel_fill_(jo, devices)
            elif jo.get("action") == "pixel-bmp":
                fun.matrix_pixel_bmp_(jo, devices)


# 登录
@app.route('/user/login', methods=['POST'])
def login():
    return fun.login_()


# 注册
@app.route('/user/register', methods=['POST'])
def register():
    return fun.register_()


# 注册验证码
@app.route('/user/register/verifyCode', methods=['POST'])
def register_verifyCode():
    return fun.register_verifyCode_()


# 获取某类型的一添加的所有设备列表
# @app.route('/devices/get/type/list/<type>', methods=['GET'])
# def devices_type_list(type):
#     return fun.devices_type_list_(type)


# 添加设备
@app.route('/devices/add', methods=["POST"])
def devices_add():
    return fun.devices_add_()


# 添加设备GPIO引脚
@app.route('/devices/gpio/add', methods=["POST"])
def devices_gpio_add():
    return fun.devices_gpio_add_()


# 添加设备Gpio引脚的任务
@app.route('/devices/gpio/task/add', methods=["POST"])
def devices_gpio_task_add():
    return fun.devices_gpio_task_add_()


# 删除设备
@app.route('/devices/del', methods=["POST"])
def devices_del():
    return fun.devices_del_()


# 设备列表
@app.route('/devices/list', methods=["POST"])
def devices_list():
    return fun.devices_list_()


# 设备详情
@app.route('/devices/info', methods=["POST"])
def devices_info():
    # fun.devices_info_()
    return ""


# 创建数据库
@app.route('/creation/database', methods=["GET"])
def creation_dataBase():
    # db.drop_all()
    # db.create_all()
    return "succeed! 以弃用"


# 获取设备类型
@app.route('/devices/type/list', methods=["POST"])
def get_devices_type_list():
    return fun.get_devices_type_list_()


# 添加设备类型
@app.route('/devices/type/add', methods=["POST"])
def devices_type_add():
    return fun.devices_type_add_()


# 修改设备名称
@app.route('/devices/edit/name', methods=["POST"])
def devices_edit_name():
    return fun.devices_edit_name_()


# 设备鉴权（登录）
@app.route('/devices/authentication', methods=["POST"])
def devices_authentication():
    # fun.devices_info_()
    a = fun.devices_authentication_()
    print(a)
    return a


# 上传Bin文件
@app.route('/ota/bin/upload', methods=["POST"])
def ota_bin_upload():
    pass


# 获取多个更新信息（app检查更新）
@app.route('/ota/info/gets', methods=["POST"])
def ota_info_gets():
    pass


# 获取更新（设备检查更新）
@app.route('/ota/get/<type>', methods=["GET"])
def ota_info_get(type):
    pass


# ota下载
@app.route('/download/ota/<type>/<name>/<code>', methods=["GET"])
def download_ota(type, name, code):
    pass


@app.route('/test', methods=["GET"])
def test():
    return "succeed!"


if __name__ == '__main__':
    # handler = logging.FileHandler('flask.log')
    # app.logger.addHandler(handler)
    mq.run(mq_call)
    app.run()

    """
    更新log
    
    2023-12之前:
        更新了设备任务（设备任务采用RabbitMq的延时插件执行）
    2023-12-3:
        预计更新登录注册
            登录:在登录后将生成长久的Token，也就是说在不从新登录，Token将不会过期
            注册:注册将采用邮箱注册，账号将由系统分配
    
    整体完成后:
        Api请求将添加校验:
            预设校验:
                时间校验，时间差不超过5秒（时间戳）
                
                参数md5校验
                
                随机数校验，随机数将缓存到redis中，每次请求检查随机数，不存在请求通过，写入随机数到redis中
                
                待定...
                
    """
