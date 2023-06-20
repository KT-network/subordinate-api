from config import db, app


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)  # 数据id
    user = db.Column(db.String(11), nullable=False)
    passwd = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(50), nullable=False)
    devices = db.relationship("Devices", backref='user', lazy='dynamic')


class Devices(db.Model):
    __tablename__ = 'devices'
    id = db.Column(db.Integer, primary_key=True)  # 数据id
    name = db.Column(db.String(11), nullable=False)
    devicesId = db.Column(db.String(255), nullable=False)
    devicesType = db.Column(db.String(100), nullable=False)
    picUrl = db.Column(db.String(255), nullable=False)
    userId = db.Column(db.Integer, db.ForeignKey('user.id'))


# class DevicesInfo(db.Model):
#     __tablename__ = 'DevicesInfo'

if __name__ == '__main__':
    db.drop_all()
    db.create_all()
