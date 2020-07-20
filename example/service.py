from nameko.rpc import rpc


class MyService:
    name = "my_service"

    @rpc
    def say_hello(self):
        return "Hello!"
