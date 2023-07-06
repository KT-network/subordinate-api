from flask import Flask, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_redis import FlaskRedis

app = Flask(__name__)
# -------------mysql配置----------------
# 设置连接数据库的URL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://whose:kunshao@127.0.0.1:3306/whose_subordinate?charset=utf8mb4'
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

app.config['REDIS_URL'] = "redis://my:kunshao@127.0.0.1:6379/0"
dbr = FlaskRedis(app)

if __name__ == '__main__':
    dbr.set("123","jdfhshdfshfusf")
    print(dbr.get("123"))