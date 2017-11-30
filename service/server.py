import threading
from flask import Blueprint, Flask, request

# config = {
#     'database' : 4242,
#     'sniffer' : 30001,
#     'graph' : 30002
# }

# config = {
#     'database' : 4243,
#     'sniffer' : 30003,
#     'graph' : 30004
# }

config = {
    'database' : 4244,
    'sniffer' : 30005,
    'graph' : 30006
}

class Server():
    """
    A server builder class.

    Each server is extendable via adding restful components.
    The underlying server is Flask.

    e.g.
      Server("test_server", "30020")
        .add_component_get("/get_route", get_component)
        .add_component_post("/post_route", post_component)
        .run()
    """
    def __init__(self, name, port):
        self.app = Flask(name)
        self.name = name
        self.port = port
        self.components = []

    def add_component_post(self, route, component):
        self.components.append(component)

        def binder():
            def binded():
                return component.receive_post()
            binded.__name__ = self.name + route.replace("/", "_")

            return binded

        self.app.route(route, methods=['POST'])(binder())
        return self

    def add_component_get(self, route, component):
        self.components.append(component)

        def binder():
            def binded():
                return component.receive_get()
            binded.__name__ = self.name + route.replace("/", "_")

            return binded

        self.app.route(route, methods=['GET'])(binder())
        return self

    def run(self):
        self.app.run(host='0.0.0.0', port=self.port)
