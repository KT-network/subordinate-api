from config import app, db
import fun


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
