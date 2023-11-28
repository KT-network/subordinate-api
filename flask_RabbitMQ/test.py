from flask import Flask
from flask_RabbitMQ import RabbitMQ

app = Flask(__name__)

app.config["RABBITMQ_HOST"] = '192.168.21.128'
app.config['RABBITMQ_USERNAME'] = 'whose'
app.config['RABBITMQ_PASSWORD'] = '123456'
app.config['RABBITMQ_VIRTUAL_HOST'] = '/whose/server'
app.config['RABBIT_DELAY_MSG_MODE'] = 'plugins'
app.config['RABBIT_EXCHANGE'] = 'whose-ks-delay-test-exc'
app.config['RABBIT_QUEUE'] = 'whose-ks-delay-test-que'
# queue = Queue()
rpc = RabbitMQ(app)


# @queue(queue='rpc-queue')
# @rpc.on_consumer
def call(ch, method, props, body):
    print(body)
    ch.basic_ack(delivery_tag=method.delivery_tag)


@app.route("/a/<num>", methods=['GET'])
def a(num):
    rpc.send(num, int(num))
    return 'test'


if __name__ == '__main__':
    rpc.run(call)
    app.run()
