import json

from config import app, db, mqtt_client
import fun
import dataBase


@mqtt_client.on_message()
def handle_message(client, userdata, msg):
    topics = msg.topic.split("/")
    if topics[len(topics) - 1] == "connected":
        jo = json.loads(msg.payload)
        userName = jo.get("username")
        userId = fun._getMd5(userName)
        if jo.get("clientid")[- 3:] == "app":
            if jo.get("clientid")[:-4] == userId:
                dataBase.User.query.filter(dataBase.User.user == userName, dataBase.User.delTime == None).update(
                    {"state": True})
                db.session.commit()

                devices = dataBase.User.query.filter(
                    dataBase.User.user == userName, dataBase.User.delTime == None
                ).first().devices.filter(
                    dataBase.Devices.delTime == None).all()
                devicesState = {}
                for item in devices:
                    devicesState.update({item.devicesId: item.state})
                mqtt_client.publish(fun.devicesStateIssueTopic(userId), json.dumps(devicesState))
        else:
            user = dataBase.User.query.filter(dataBase.User.user == userName, dataBase.User.delTime == None).first()
            if user is not None:
                user.devices.filter(dataBase.Devices.delTime == None,
                                    dataBase.Devices.devicesId == jo.get("clientid")).update(
                    {"state": True})
                db.session.commit()
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
                    dataBase.User.user == userName, dataBase.User.delTime == None).update(
                    {"state": False})
                db.session.commit()
        else:
            user = dataBase.User.query.filter(dataBase.User.user == userName, dataBase.User.delTime == None).first()
            if user is not None:
                user.devices.filter(dataBase.Devices.delTime == None,
                                    dataBase.Devices.devicesId == jo.get("clientid")).update(
                    {"state": False})
                db.session.commit()
                if user.state:
                    devices = user.devices.filter(dataBase.Devices.delTime == None).all()
                    devicesState = {}
                    for item in devices:
                        devicesState.update({item.devicesId: item.state})
                    mqtt_client.publish(fun.devicesStateIssueTopic(userId), json.dumps(devicesState))
                    # mqtt_client.unsubscribe(fun.appSubscribeTopic(userId, jo.get("clientid")))

    elif topics[len(topics) - 1] == "action":
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
            fun.switch_task_add(jo, devicesId)


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
@app.route('/devices/get/type/list/<type>', methods=['GET'])
def devices_type_list(type):
    return fun.devices_type_list_(type)


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
@app.route('/devices/add', methods=["POST"])
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
    db.drop_all()
    db.create_all()
    return "succeed!"


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


if __name__ == '__main__':
    app.run("0.0.0.0", 1166)
