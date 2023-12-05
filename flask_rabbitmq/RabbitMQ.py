import threading
from typing import Callable

import pika
from flask import Flask


class RabbitMQ(object):
    def __init__(self, app: Flask = None):
        self.app = app
        # self.config = self.app.config

        self.rabbitmq_server_host = None
        self.rabbitmq_server_username = None
        self.rabbitmq_server_password = None
        self.rabbitmq_server_virtual_host = None
        # self.rabbitmq_server_delay_msg = False
        self.rabbitmq_server_delay_msg_mode = None

        self._connection = None
        self._channel_p = None
        self._channel_c = None

        self._exchange = None
        self._queue = None

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        if self.app is None:
            self.app = app

        self.valid_config()
        self.connect_rabbitmq_server()
        # self._channel_c.basic_consume(queue='server', on_message_callback=self.on_consumer, auto_ack=True)

    def valid_config(self):
        if not self.app.config.get('RABBITMQ_HOST'):
            raise Exception("The rabbitMQ application must configure host.")
        self.rabbitmq_server_host = self.app.config.get('RABBITMQ_HOST')
        self.rabbitmq_server_username = self.app.config.get('RABBITMQ_USERNAME')
        self.rabbitmq_server_password = self.app.config.get('RABBITMQ_PASSWORD')
        self.rabbitmq_server_virtual_host = '/' if self.app.config.get(
            "RABBITMQ_VIRTUAL_HOST") is None else self.app.config.get("RABBITMQ_VIRTUAL_HOST")
        # self.rabbitmq_server_delay_msg = False if self.config.get("RABBITMQ_DELAY_MSG") is None else True
        self.rabbitmq_server_delay_msg_mode = self.app.config.get("RABBIT_DELAY_MSG_MODE")
        self._queue = self.app.config.get("RABBIT_QUEUE")
        self._exchange = self.app.config.get("RABBIT_EXCHANGE")

    def connect_rabbitmq_server(self):

        if self.rabbitmq_server_username != None and self.rabbitmq_server_password != None:
            credentials = pika.PlainCredentials(self.rabbitmq_server_username, self.rabbitmq_server_password)

            self._connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.rabbitmq_server_host,
                    virtual_host=self.rabbitmq_server_virtual_host,
                    credentials=credentials))
        elif self.rabbitmq_server_username != None and self.rabbitmq_server_password == None:
            credentials = pika.PlainCredentials(self.rabbitmq_server_username, '')
            self._connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.rabbitmq_server_host,
                    virtual_host=self.rabbitmq_server_virtual_host,
                    credentials=credentials))

        else:
            parameters = pika.ConnectionParameters(host=self.rabbitmq_server_host,
                                                   virtual_host=self.rabbitmq_server_virtual_host)
            self._connection = pika.BlockingConnection(parameters)

        self._channel_p = self._connection.channel()
        self._channel_c = self._connection.channel()

        if self.rabbitmq_server_delay_msg_mode == 'dead-letter':
            pass
        elif self.rabbitmq_server_delay_msg_mode == 'plugins':
            self._channel_p.exchange_declare(exchange=self._exchange, exchange_type="x-delayed-message",
                                             arguments={'x-delayed-type': 'direct'})

            self._channel_p.queue_declare(queue=self._queue, durable=True)
            self._channel_p.queue_bind(exchange=self._exchange, queue=self._queue)

            self._channel_c.exchange_declare(exchange=self._exchange, exchange_type="x-delayed-message",
                                             arguments={'x-delayed-type': 'direct'})
            self._channel_c.queue_declare(queue=self._queue, durable=True)
            self._channel_c.queue_bind(exchange=self._exchange, queue=self._queue)

        else:
            self._channel_p.queue_declare(queue=self._queue, durable=True)
            self._channel_c.queue_declare(queue=self._queue, durable=True)

    # def send(self, msg):
    #     self._channel_p.basic_publish(exchange='',
    #                                   routing_key='server',
    #                                   body=msg,
    #                                   properties=pika.BasicProperties(delivery_mode=2, ))

    def on_consumer(self, call):
        def wrapper(ch, method, properties, body):
            call(ch, method, properties, body)

        return wrapper

    def send(self, msg, delay=None):
        if self.rabbitmq_server_delay_msg_mode == 'plugins':
            if delay is None:
                self._channel_p.basic_publish(exchange=self._exchange,
                                              routing_key=self._queue,
                                              body=msg)
            else:
                print("mq", delay)
                self._channel_p.basic_publish(exchange=self._exchange,
                                              routing_key=self._queue,
                                              body=msg,
                                              properties=pika.BasicProperties(delivery_mode=2,
                                                                              headers={'x-delay': delay * 1000}))
        elif self.rabbitmq_server_delay_msg_mode == "dead-letter":
            pass
        else:
            self._channel_p.basic_publish(exchange=self._exchange,
                                          routing_key=self._queue,
                                          body=msg)

    def consuming(self):
        self._channel_c.start_consuming()

    def run(self, call):
        self._channel_c.basic_consume(queue=self._queue, auto_ack=False, on_message_callback=call)
        t = threading.Thread(target=self.consuming)
        t.start()

# def on_consumer(self):
#     def decorator(handler: Callable) -> Callable:
#         def call(ch, method, properties, body):
#             handler(body)
#
#         self._channel_con.basic_consume(queue='server', on_message_callback=call, auto_ack=True)
#
#         return decorator
