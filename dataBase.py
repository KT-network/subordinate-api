from config import db, app

from enum import Enum


class UserRole(Enum):
    SUPER_USER = 0
    ADMIN_USER = 1
    NORMAL_USER = 2


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)  # 数据id
    user = db.Column(db.String(11), nullable=False)
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
    devicesType = db.Column(db.String(100), nullable=False)
    picUrl = db.Column(db.String(255), nullable=False)
    state = db.Column(db.Boolean, default=False)
    userId = db.Column(db.Integer, db.ForeignKey('user.id'))
    dev_state = db.relationship("DevicesHistoryState", backref='devices', lazy='dynamic')
    createTime = db.Column(db.DateTime)
    delTime = db.Column(db.DateTime)


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
    type = db.Column(db.String(255), nullable=False)
    picUrl = db.Column(db.String(255), nullable=False)
    size = db.Column(db.String(20), nullable=True)
    createTime = db.Column(db.DateTime)
    delTime = db.Column(db.DateTime)


if __name__ == '__main__':
    db.drop_all()
    db.create_all()
