from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from flask import Flask, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_redis import FlaskRedis
from flask_mqtt import Mqtt
from flask_apscheduler import APScheduler

app = Flask(__name__)

# -------------mysql配置----------------

# 设置连接数据库的URL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://whose:kunshao@192.168.1.150:3306/subordinate?charset=utf8mb4'
# 设置每次请求结束后会自动提交数据库中的改动
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
# 隐藏不必要的报错
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

app.app_context().push()

db = SQLAlchemy(app=app)

# -------------邮箱配置----------------

# 如果是qq邮箱这里应该为"smtp.qq.com"
app.config['MAIL_SERVER'] = "smtp.qq.com"
# 如果使用ssl则端口号应为465
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
# 发送人的邮箱
app.config['MAIL_USERNAME'] = "kt_network@qq.com"
# 这里的密码是之前获取的邮箱授权码
app.config['MAIL_PASSWORD'] = "tkqcyxgdaisiddjh"
# 显示发送人的名字
app.config['MAIL_DEFAULT_SENDER'] = 'kt_network@qq.com'
mail = Mail(app)

# -------------redis配置----------------

app.config['REDIS_URL'] = "redis://:kunshao@192.168.1.150:6379/0"
dbr = FlaskRedis(app)

# -------------mqtt配置----------------

app.config['MQTT_BROKER_URL'] = '192.168.1.150'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_USERNAME'] = 'services'  # 当你需要验证用户名和密码时，请设置该项
app.config['MQTT_PASSWORD'] = '123456'  # 当你需要验证用户名和密码时，请设置该项
app.config['MQTT_KEEPALIVE'] = 5  # 设置心跳时间，单位为秒
app.config['MQTT_TLS_ENABLED'] = False  # 如果你的服务器支持 TLS，请设置为 True
app.config['MQTT_CLIENT_ID'] = 'services'
mqtt_client = Mqtt(app)

# 设备（app）上线话题
topicConnected = "$SYS/brokers/+/clients/+/connected"
# 设备（app）掉线话题
topicDisconnected = "$SYS/brokers/+/clients/+/disconnected"
# app消息话题 userid,devicesId
topicAppMsg = "ks/general/+/+/action"
# 设备消息话题  devicesId,userid
topicDevicesMsg = "ks/subordinate/+/+/action"


@mqtt_client.on_connect()
def handle_connect(client, userdata, flags, rc):
    if rc == 0:
        print('Mqtt Connected successfully')
        mqtt_client.subscribe(topicConnected)
        mqtt_client.subscribe(topicDisconnected)
        mqtt_client.subscribe(topicAppMsg)
        mqtt_client.subscribe(topicDevicesMsg)
    else:
        print('Bad connection. Code:', rc)


# -------------APScheduler配置----------------

class Config:
    SCHEDULER_JOBSTORES = {
        'default': SQLAlchemyJobStore(
            url='mysql+pymysql://whose:kunshao@192.168.1.150:3306/subordinate?charset=utf8mb4')
    }
    SCHEDULER_API_ENABLED = True


app.config.from_object(Config)
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

if __name__ == '__main__':
    dbr.set("123", "jdfhshdfshfusf")
    print(dbr.get("123"))
