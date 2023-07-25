from config import db, app

from enum import Enum


class UserRole(Enum):
    SUPER_USER = 0
    ADMIN_USER = 1
    NORMAL_USER = 2


class ProgramType(Enum):
    PIXEL_SCREEN_21_29 = 0  # 21*29像素
    USER_CUSTOM = 1  # 自定义像素（涂鸦）
    USER_TEXT = 2  # 自定义Text（文本）


class ConfigType(Enum):
    SWITCH = 0
    PROGRAM = 1


# 开关型的值
class SwitchValue(Enum):
    OPEN = 0  # 只开
    CLOSE = 1  # 只关
    FLICKER = 2  # 开->关->开


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)  # 数据id
    user = db.Column(db.String(11), nullable=False)
    userId = db.Column(db.String(255), nullable=False)
    passwd = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(50), nullable=False)

    devices = db.relationship("Devices", backref='user', lazy='dynamic')

    role = db.Column(db.Enum(UserRole), default=UserRole.NORMAL_USER)
    state = db.Column(db.Boolean, default=False)
    createTime = db.Column(db.DateTime)
    delTime = db.Column(db.DateTime)


class Devices(db.Model):
    __tablename__ = 'devices'
    id = db.Column(db.Integer, primary_key=True)  # 数据id
    name = db.Column(db.String(11), nullable=False)
    devicesId = db.Column(db.String(255), nullable=False)
    devicesType = db.Column(db.Integer, db.ForeignKey('devicestype.id'))
    picUrl = db.Column(db.String(255), nullable=False)
    state = db.Column(db.Boolean, default=False)

    userId = db.Column(db.Integer, db.ForeignKey('user.id'))

    dev_state = db.relationship("DevicesHistoryState", backref='devices', lazy='dynamic')
    # config = relationship("DevicesConfig", backref="devices", lazy="dynamic")
    gpio = db.relationship("Gpio", backref="devices", lazy="dynamic")
    createTime = db.Column(db.DateTime)
    delTime = db.Column(db.DateTime)


# class Devices(db.Model):
#     __tablename__ = 'devices'
#     id = db.Column(db.Integer, primary_key=True)  # 数据id
#     name = db.Column(db.String(11), nullable=False)
#     devicesId = db.Column(db.String(255), nullable=False)
#     devicesType = db.Column(db.String(100), nullable=False)
#     picUrl = db.Column(db.String(255), nullable=False)
#     state = db.Column(db.Boolean, default=False)
#     userId = db.Column(db.Integer, db.ForeignKey('user.id'))
#     dev_state = db.relationship("DevicesHistoryState", backref='devices', lazy='dynamic')
#     createTime = db.Column(db.DateTime)
#     delTime = db.Column(db.DateTime)


# class DevicesInfo(db.Model):
#     __tablename__ = 'DevicesInfo'


class DevicesHistoryState(db.Model):
    __tablename__ = 'deviceshistorystate'
    id = db.Column(db.Integer, primary_key=True)  # 数据id
    date = db.Column(db.DateTime, nullable=False)
    state = db.Column(db.Boolean, nullable=False)
    devicesId = db.Column(db.Integer, db.ForeignKey('devices.id'))


class DevicesType(db.Model):
    __tablename__ = 'devicestype'
    id = db.Column(db.Integer, primary_key=True)  # 数据id
    name = db.Column(db.String(11), nullable=False)
    typeName = db.Column(db.String(255), nullable=False)
    type = db.Column(db.Enum(ConfigType), nullable=False)
    gpio = db.Column(db.Integer, nullable=True)  # 设备类型默认的gpio
    picUrl = db.Column(db.String(255), nullable=False)
    size = db.Column(db.String(20), nullable=True)
    devices = db.relationship("Devices", backref="devicestype", lazy="dynamic")
    createTime = db.Column(db.DateTime)
    delTime = db.Column(db.DateTime)


class Gpio(db.Model):
    __tablename__ = 'gpio'
    id = db.Column(db.Integer, primary_key=True)  # 数据id
    devicesId = db.Column(db.Integer, db.ForeignKey('devices.id'))  # 设备id
    io = db.Column(db.Integer, nullable=False)  # 引脚
    name = db.Column(db.String(20), nullable=False)  # 引脚名称
    icon = db.Column(db.String(255), nullable=True)  # 引脚图片
    type = db.Column(db.Enum(ConfigType), default=ConfigType.SWITCH)  # 配置类型（开关型，节目型）
    state = db.Column(db.Boolean, default=False, nullable=True)  # 引脚状态（如果是节目类型，就是息屏）
    switch = db.relationship("SwitchGpio", backref="gpio", lazy="dynamic")
    # program = db.relationship("ProgramGpio", backref="gpio", lazy="dynamic")
    createTime = db.Column(db.DateTime)
    delTime = db.Column(db.DateTime)


class SwitchGpio(db.Model):
    __tablename__ = 'switch'
    id = db.Column(db.Integer, primary_key=True)  # 数据id
    gpioId = db.Column(db.Integer, db.ForeignKey('gpio.id'))  # gpio id
    taskId = db.Column(db.String(255), nullable=False)  # 任务id
    taskName = db.Column(db.String(20), nullable=False)  # 任务名称
    value = db.Column(db.Enum(SwitchValue), nullable=False)  # 值
    # state = db.Column(db.Boolean, default=False, nullable=False)  # 开关状态
    interval = db.Column(db.String(255), nullable=True)  # 保持间隔
    lasting = db.Column(db.Integer, nullable=False)  # 保持
    startDate = db.Column(db.String(255), nullable=True)  # 开始时间
    destroyDate = db.Column(db.String(255), nullable=True)  # 结束时间
    finish = db.Column(db.Boolean, default=False)  # 完成的操作
    createTime = db.Column(db.DateTime)
    delTime = db.Column(db.DateTime)

if __name__ == '__main__':
    db.drop_all()
    db.create_all()
