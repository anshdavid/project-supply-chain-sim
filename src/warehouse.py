import simpy


class Warehouse:
    def __init__(self, env: simpy.Environment) -> None:

        self.env = env

        self.products = simpy.Container(self.env, 1000)

    def get(self, amount: int = -1): ...

    def put(self): ...
