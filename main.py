from config import app
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


# 检查设备是否已被添加过
pass


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





if __name__ == '__main__':
    app.run()
